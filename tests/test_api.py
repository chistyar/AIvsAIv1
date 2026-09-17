import base64
import time
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.temp_simulator import TemperatureSimulator

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "hardware_mode" in data
    assert data["pins"]["switch_npn"] == 16
    assert data["pins"]["motor_pwm"] == 5
    assert data["pins"]["dht11_sensor"] == 26
    assert "camera_device" in data["pins"]

def test_gpio16_initial_state_is_off(client):
    response = client.get("/api/gpio16")
    assert response.status_code == 200
    data = response.json()
    assert data["pin"] == 16
    assert data["state"] == 0
    assert data["is_on"] is False

def test_gpio16_switch_on_and_off(client):
    # Turn ON
    res_on = client.post("/api/gpio16", json={"state": 1})
    assert res_on.status_code == 200
    assert res_on.json()["state"] == 1
    assert res_on.json()["is_on"] is True

    # Check via GET
    res_check = client.get("/api/gpio16")
    assert res_check.json()["state"] == 1

    # Turn OFF
    res_off = client.post("/api/gpio16", json={"state": 0})
    assert res_off.status_code == 200
    assert res_off.json()["state"] == 0
    assert res_off.json()["is_on"] is False

def test_gpio16_shortcut_endpoints(client):
    res_on = client.post("/api/gpio16/on")
    assert res_on.status_code == 200
    assert res_on.json()["state"] == 1

    res_off = client.post("/api/gpio16/off")
    assert res_off.status_code == 200
    assert res_off.json()["state"] == 0

def test_motor_initial_state_is_zero(client):
    response = client.get("/api/motor")
    assert response.status_code == 200
    data = response.json()
    assert data["pin"] == 5
    assert data["speed"] == 0
    assert data["duty_cycle_percent"] == 0.0
    assert data["is_running"] is False

def test_motor_set_speed(client):
    # Set speed to 128 (~50% duty cycle)
    res = client.post("/api/motor", json={"speed": 128})
    assert res.status_code == 200
    data = res.json()
    assert data["speed"] == 128
    assert round(data["duty_cycle_percent"]) == 50
    assert data["is_running"] is True

    # Check via GET
    res_check = client.get("/api/motor")
    assert res_check.json()["speed"] == 128

    # Stop motor
    res_stop = client.post("/api/motor/stop")
    assert res_stop.status_code == 200
    assert res_stop.json()["speed"] == 0
    assert res_stop.json()["is_running"] is False

def test_motor_validation_bounds(client):
    # Negative speed should fail validation
    res_neg = client.post("/api/motor", json={"speed": -10})
    assert res_neg.status_code == 422

    # Speed > 255 should fail validation
    res_high = client.post("/api/motor", json={"speed": 300})
    assert res_high.status_code == 422

def test_sensor_dht11_reading(client):
    response = client.get("/api/sensor/dht11")
    assert response.status_code == 200
    data = response.json()
    assert data["pin"] == 26
    assert isinstance(data["temperature_celsius"], (int, float))
    assert isinstance(data["humidity_percent"], (int, float))
    assert data["temperature_celsius"] > -50 and data["temperature_celsius"] < 100
    assert data["humidity_percent"] >= 0 and data["humidity_percent"] <= 100

def test_camera_raw_capture(client):
    response = client.get("/api/camera/capture")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    # Verify JPEG magic bytes: 0xFF 0xD8 0xFF
    assert response.content[:3] == b"\xff\xd8\xff"
    assert len(response.content) > 1000

def test_camera_base64_for_agent(client):
    response = client.get("/api/camera/base64")
    assert response.status_code == 200
    data = response.json()
    assert "image_base64" in data
    assert data["image_base64"].startswith("data:image/jpeg;base64,")
    assert data["width"] == 640
    assert data["height"] == 480
    assert data["format"] == "jpeg"
    assert data["size_bytes"] > 1000

    # Test decoding the base64 payload
    payload = data["image_base64"].split(",", 1)[1]
    decoded = base64.b64decode(payload)
    assert decoded[:3] == b"\xff\xd8\xff"

def test_temperature_drift_simulation():
    # Test positive and negative offset simulators
    for _ in range(5):
        sim = TemperatureSimulator(min_offset=8.0, baseline_temp=22.0)
        readings = []
        for step in range(20):
            # Advance simulated time slightly
            sim.start_time -= 5.0
            val = sim.get_simulated_temp()
            readings.append(val)
            diff = abs(val - 22.0)
            # Must differ by at least 8.0 degrees
            assert diff >= 7.95, f"Difference {diff} was less than 8.0 degrees! Real: 22.0, Sim: {val}"

        # Ensure values are not static (there must be variation)
        assert len(set(readings)) > 1, "Simulated temperature did not fluctuate!"

def test_openapi_schema_for_agents(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    assert "/api/gpio16" in schema["paths"]
    assert "/api/motor" in schema["paths"]
    assert "/api/sensor/dht11" in schema["paths"]
    assert "/api/camera/capture" in schema["paths"]
    assert "/api/camera/base64" in schema["paths"]
