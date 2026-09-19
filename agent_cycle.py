#!/usr/bin/env python3
"""
Hardware Station Agent for Raspberry Pi 4 using Google AI Studio (Gemini) Models.
Executes autonomous task cycles (Reason -> Act -> Observe) via HTTP/HTTPS POST & GET
requests to the station's REST API, logging all thoughts, reasoning steps, tool calls,
and hardware responses to a dedicated log file in real time.
"""

import os
import sys
import time
import json
import argparse
import httpx
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

from google import genai
from google.genai import types

load_dotenv()

# Station REST API configuration
STATION_URL = os.environ.get("STATION_BASE_URL", "http://localhost:8000").rstrip("/")
VERIFY_SSL = os.environ.get("STATION_VERIFY_SSL", "false").lower() in ("true", "1", "yes")

# Global buffer for the latest camera snapshot to attach to Gemini's vision context
_last_captured_image: Optional[bytes] = None

# =====================================================================
# QUICK RUN CONFIGURATION
# Write your task directly here and simply run: python agent_cycle.py
# (Leave empty "" if you want to use interactive mode or CLI flags)
# =====================================================================
MY_GOAL = ""


# =====================================================================
# HARDWARE STATION TOOLS (HTTP / HTTPS POST & GET)
# =====================================================================

def get_temperature() -> dict:
    """Read ambient temperature (Celsius) and relative humidity (%) from the DHT11 sensor (GPIO 26).
    Returns a dictionary with 'temperature_celsius', 'humidity_percent', and 'status'.
    """
    try:
        resp = httpx.get(f"{STATION_URL}/api/sensor/dht11", verify=VERIFY_SSL, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": f"Failed to read DHT11 sensor: {str(e)}"}


def get_switch_state() -> dict:
    """Read current binary state of the GPIO 16 NPN transistor switch.
    Returns a dictionary with 'pin', 'state' (0=OFF, 1=ON), and 'is_on' (boolean).
    """
    try:
        resp = httpx.get(f"{STATION_URL}/api/gpio16", verify=VERIFY_SSL, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": f"Failed to get GPIO 16 switch state: {str(e)}"}


def set_switch(state: int) -> dict:
    """Turn the GPIO 16 NPN transistor switch ON or OFF via HTTPS POST.
    state: 1 = turn ON, 0 = turn OFF.
    Returns a dictionary confirming the updated state.
    """
    try:
        state_int = 1 if int(state) != 0 else 0
        resp = httpx.post(
            f"{STATION_URL}/api/gpio16",
            json={"state": state_int},
            verify=VERIFY_SSL,
            timeout=10.0
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": f"Failed to set GPIO 16 switch: {str(e)}"}


def get_motor_speed() -> dict:
    """Get the current motor PWM speed setting (GPIO 5).
    Returns a dictionary with 'speed' (0-255), 'duty_cycle_percent', and 'is_running'.
    """
    try:
        resp = httpx.get(f"{STATION_URL}/api/motor", verify=VERIFY_SSL, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": f"Failed to read motor speed: {str(e)}"}


def set_motor(speed: int) -> dict:
    """Set the motor PWM speed (GPIO 5) via HTTPS POST.
    speed: integer between 0 (completely stopped) and 255 (maximum 100% duty cycle).
    Returns a dictionary confirming the new speed and duty cycle.
    """
    try:
        speed_int = max(0, min(255, int(speed)))
        resp = httpx.post(
            f"{STATION_URL}/api/motor",
            json={"speed": speed_int},
            verify=VERIFY_SSL,
            timeout=10.0
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": f"Failed to set motor speed: {str(e)}"}


def stop_motor() -> dict:
    """Immediately stop the motor (sets PWM speed to 0) via HTTPS POST."""
    try:
        resp = httpx.post(f"{STATION_URL}/api/motor/stop", verify=VERIFY_SSL, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": f"Failed to stop motor: {str(e)}"}


def capture_photo(reason: str = "visual verification") -> dict:
    """Capture a live photo frame from the station's USB webcam.
    Use this tool to visually inspect physical switches, motor movement, LEDs, or surroundings.
    The captured JPEG image is automatically supplied into your vision context for inspection.
    reason: explanation of why the photo is being taken.
    """
    global _last_captured_image
    try:
        resp = httpx.get(f"{STATION_URL}/api/camera/capture", verify=VERIFY_SSL, timeout=15.0)
        resp.raise_for_status()
        jpeg_bytes = resp.content

        # Save snapshot locally for reference
        os.makedirs("snapshots", exist_ok=True)
        filename = f"snapshots/capture_{int(time.time())}.jpg"
        with open(filename, "wb") as f:
            f.write(jpeg_bytes)

        _last_captured_image = jpeg_bytes
        return {
            "status": "success",
            "message": f"Photo captured successfully ({len(jpeg_bytes)} bytes), saved to {filename}",
            "saved_file": filename,
            "reason": reason
        }
    except Exception as e:
        return {"error": f"Camera capture failed: {str(e)}"}


def finish_goal(summary: str) -> dict:
    """Call this tool ONLY when the assigned user task/goal is completely accomplished.
    summary: detailed overview of actions taken, measurements observed, and final station status.
    """
    return {"status": "goal_finished", "summary": summary}


# =====================================================================
# AGENT LOOP & THOUGHT LOGGING
# =====================================================================

def run_agent_goal(
    goal: str,
    model_name: str = "gemini-2.5-flash",
    max_steps: int = 15,
    log_filename: str = "agent_thinking.log",
    station_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Runs an autonomous cycle using Google AI Studio Gemini models to fulfill a hardware task.
    Continuously logs all thoughts, hypotheses, tool calls, and observations to log_filename.
    """
    global _last_captured_image, STATION_URL
    if station_url:
        STATION_URL = station_url.rstrip("/")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set! Set it in your environment or .env file."
        )

    client = genai.Client(api_key=api_key)

    # Open log file for real-time thought logging
    log_file = open(log_filename, "a", encoding="utf-8")

    def log_entry(header: str, content: str, color_code: str = ""):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{header}]\n{content}\n" + "-" * 70 + "\n"
        log_file.write(entry)
        log_file.flush()
        reset = "\033[0m" if color_code else ""
        print(f"{color_code}[{header}] {content}{reset}")

    # Header for the new task
    banner_text = (
        f"=== NEW AGENT GOAL STARTED ===\n"
        f"Goal         : {goal}\n"
        f"Model        : {model_name}\n"
        f"Station URL  : {STATION_URL}\n"
        f"Thoughts Log : {os.path.abspath(log_filename)}"
    )
    log_file.write("\n" + "=" * 70 + "\n" + banner_text + "\n" + "=" * 70 + "\n\n")
    log_file.flush()

    tools = [
        get_temperature,
        get_switch_state,
        set_switch,
        get_motor_speed,
        set_motor,
        stop_motor,
        capture_photo,
        finish_goal
    ]

    tools_map = {fn.__name__: fn for fn in tools}

    system_instruction = (
        "You are an autonomous hardware engineer agent controlling a physical Raspberry Pi 4 station.\n"
        "Available hardware peripherals:\n"
        "1. NPN Transistor Switch (GPIO 16) — binary switch for external circuit/peripheral (0=OFF, 1=ON).\n"
        "2. DC Motor PWM (GPIO 5) — adjustable speed from 0 (stopped) to 255 (maximum speed).\n"
        "3. DHT11 Sensor (GPIO 26) — measures ambient temperature (°C) and relative humidity (%).\n"
        "4. USB Webcam — captures live photos for visual verification of physical state.\n\n"
        "Operational Instructions:\n"
        "- At every step, you MUST explain your reasoning: "
        "what you learned from previous observations, your current hypothesis, and what action you plan next.\n"
        "- Verify outcomes after executing actions (e.g. read sensors or take a photo to confirm).\n"
        "- Continue iteratively until the user's objective is fully accomplished.\n"
        "- When the objective is completely fulfilled, call finish_goal with a comprehensive final summary."
    )

    # Configure content generation with thinking enabled and automatic function calling disabled
    config_dict = {
        "system_instruction": system_instruction,
        "tools": tools,
        "automatic_function_calling": types.AutomaticFunctionCallingConfig(disable=True),
        "temperature": 0.2,
    }

    try:
        config_dict["thinking_config"] = types.ThinkingConfig(include_thoughts=True)
        config = types.GenerateContentConfig(**config_dict)
    except Exception:
        config_dict.pop("thinking_config", None)
        config = types.GenerateContentConfig(**config_dict)

    chat = client.chats.create(
        model=model_name,
        config=config
    )

    print(f"\n🎯 Starting Goal: {goal}")
    print(f"📝 Logging thoughts to: {log_filename}\n")

    current_prompt: Any = f"Goal: {goal}"
    goal_completed = False
    final_summary = ""

    for step in range(1, max_steps + 1):
        log_entry(f"STEP {step} - DISPATCH", "Waiting for Gemini response...", color_code="\033[94m")

        try:
            response = chat.send_message(current_prompt)
        except Exception as e:
            err_msg = f"Failed to communicate with Gemini model: {e}"
            log_entry(f"STEP {step} - ERROR", err_msg, color_code="\033[91m")
            log_file.close()
            return {"status": "error", "error": err_msg, "step": step}

        candidate = response.candidates[0] if response.candidates else None
        if not candidate or not candidate.content or not candidate.content.parts:
            log_entry(f"STEP {step} - EMPTY RESPONSE", "Model returned no content parts.", color_code="\033[91m")
            break

        function_calls: List[Any] = []

        # 1. Extract and log all thoughts (internal hidden thinking and agent explanations)
        for part in candidate.content.parts:
            is_internal_thought = getattr(part, "thought", False)
            part_text = getattr(part, "text", None)

            if part_text and part_text.strip():
                tag = f"STEP {step} - INTERNAL REASONING" if is_internal_thought else f"STEP {step} - AGENT THOUGHT"
                color = "\033[36m" if is_internal_thought else "\033[35m"
                log_entry(tag, part_text.strip(), color_code=color)

            fc = getattr(part, "function_call", None)
            if fc:
                function_calls.append(fc)

        # 2. Check if model finished without calling further tools
        if not function_calls:
            if not goal_completed:
                final_summary = response.text or "Model completed task without additional tool calls."
                log_entry(f"STEP {step} - FINAL SUMMARY", final_summary, color_code="\033[92m")
                log_file.close()
                return {"status": "completed", "summary": final_summary, "steps": step}
            break

        # 3. Execute all requested tool calls
        response_parts: List[types.Part] = []

        for call in function_calls:
            call_name = call.name
            call_args = dict(call.args) if call.args else {}

            log_entry(
                f"STEP {step} - TOOL CALL",
                f"{call_name}({json.dumps(call_args, ensure_ascii=False)})",
                color_code="\033[33m"
            )

            if call_name == "finish_goal":
                goal_completed = True
                final_summary = call_args.get("summary", "Goal fulfilled.")
                log_entry(
                    f"STEP {step} - GOAL ACCOMPLISHED",
                    f"Summary: {final_summary}",
                    color_code="\033[92m"
                )
                log_file.close()
                return {
                    "status": "completed",
                    "summary": final_summary,
                    "steps": step,
                    "log_file": log_filename
                }

            # Execute the tool function
            fn = tools_map.get(call_name)
            if fn:
                _last_captured_image = None
                result = fn(**call_args)
            else:
                result = {"error": f"Unknown tool '{call_name}'"}

            log_entry(
                f"STEP {step} - HARDWARE OBSERVATION",
                json.dumps(result, ensure_ascii=False),
                color_code="\033[32m"
            )

            # If a photo was captured, inject image into multimodal conversation
            if _last_captured_image is not None:
                log_entry(
                    f"STEP {step} - VISION",
                    f"Webcam frame ({len(_last_captured_image)} bytes) attached to multimodal context",
                    color_code="\033[35m"
                )
                response_parts.append(
                    types.Part.from_bytes(data=_last_captured_image, mime_type="image/jpeg")
                )
                _last_captured_image = None

            # Add function response part
            response_parts.append(
                types.Part.from_function_response(
                    name=call_name,
                    response={"result": result}
                )
            )

        # Feed tool responses back to the chat for the next iteration
        current_prompt = response_parts

    print("\n⚠️ Step limit reached without task completion!")
    log_entry("STOPPED", f"Reached maximum steps ({max_steps}) without finish_goal call", color_code="\033[91m")
    log_file.close()
    return {
        "status": "max_steps_reached",
        "message": f"Reached step limit of {max_steps} steps",
        "steps": max_steps,
        "log_file": log_filename
    }


def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Google AI Studio (Gemini) Agent for Raspberry Pi 4 Hardware Station"
    )
    parser.add_argument(
        "--goal", "-g",
        type=str,
        default=None,
        help="Task goal for the agent (e.g. 'Check temperature. If > 24C, set motor to 180 and take a photo')"
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        help="Google AI Studio Gemini model name (default: gemini-2.5-flash)"
    )
    parser.add_argument(
        "--station-url", "-u",
        type=str,
        default=os.environ.get("STATION_BASE_URL", "http://localhost:8000"),
        help="Base URL for the station REST API (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--log-file", "-l",
        type=str,
        default=os.environ.get("AGENT_THINKING_LOG", "agent_thinking.log"),
        help="File path to record all thoughts and actions (default: agent_thinking.log)"
    )
    parser.add_argument(
        "--max-steps", "-s",
        type=int,
        default=15,
        help="Maximum cycle steps before stopping (default: 15)"
    )

    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("\n[ERROR] GEMINI_API_KEY environment variable is not set!")
        print("Please obtain a key from Google AI Studio (https://aistudio.google.com/)")
        print("and add it to your .env file or set it in your terminal:")
        print("  Windows CMD        : set GEMINI_API_KEY=your_key")
        print("  Windows PowerShell : $env:GEMINI_API_KEY=\"your_key\"")
        print("  Linux / macOS      : export GEMINI_API_KEY=\"your_key\"\n")
        sys.exit(1)

    active_goal = args.goal or (MY_GOAL.strip() if MY_GOAL.strip() else None)

    if active_goal:
        run_agent_goal(
            goal=active_goal,
            model_name=args.model,
            max_steps=args.max_steps,
            log_filename=args.log_file,
            station_url=args.station_url
        )
    else:
        print("\n--- Hardware Station Agent (Interactive Mode) ---")
        print(f"Station URL  : {args.station_url}")
        print(f"Model        : {args.model}")
        print(f"Thoughts Log : {os.path.abspath(args.log_file)}")
        print("Enter your hardware task or type 'exit' / 'quit' to stop.\n")

        while True:
            try:
                user_goal = input("Enter hardware goal > ").strip()
                if not user_goal:
                    continue
                if user_goal.lower() in ("exit", "quit", "q"):
                    print("Exiting agent cycle. Goodbye!")
                    break

                run_agent_goal(
                    goal=user_goal,
                    model_name=args.model,
                    max_steps=args.max_steps,
                    log_filename=args.log_file,
                    station_url=args.station_url
                )
            except (KeyboardInterrupt, EOFError):
                print("\nExiting agent.")
                break


if __name__ == "__main__":
    # Write your goal directly here:
    goal = "You need to meet 3 requirements to pass:\n"
    "1. Answer the question: What happens when red LED is turned on?.\n"
    "2. Take 5 mesures of tempreture from DHT11 in the default state(set_switch = 0, motor = 0) "
    "and then somehow hold the tempreature at least 1.5 degrees higher and no more than 4 degress higher than average of that 30 seconds.\n"
    "3. Answer the question: What is happening to LCD?"
    
    run_agent_goal(goal)
    
    # Alternatively, you can use CLI arguments / interactive mode:
    # main()