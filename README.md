# Raspberry Pi 4 Hardware Gateway (Docker + FastAPI)

Микросервис для управления аппаратной частью **Raspberry Pi 4** (ОС Debian 13 Trixie / Bookworm) через HTTP REST API с поддержкой **USB веб-камеры**, динамического вывода температуры на **LCD 1602** и автоматической генерацией схемы вызова функций (**Function Calling / Tool Use**) для ИИ-агентов и сторонних микросервисов.

---

## 📌 Распиновка подключения (BCM Pinout)

| Устройство | Пин Raspberry Pi (BCM) | Физический номер пина (Header) | Назначение |
| :--- | :--- | :--- | :--- |
| **NPN-транзистор (Ключ)** | **GPIO 16** | Пин 36 | База транзистора (0 = выключен, 1 = включен) |
| **NPN-транзистор (Мотор)**| **GPIO 5** | Пин 29 | База транзистора, ШИМ 0–255 (дефолт 0) |
| **DHT11 (Датчик t°)** | **GPIO 26** | Пин 37 | Data pin датчика (опрос строго по запросу) |
| **LCD 1602 (I2C SDA)** | **GPIO 2 (SDA)** | Пин 3 | Данные шины I2C |
| **LCD 1602 (I2C SCL)** | **GPIO 3 (SCL)** | Пин 5 | Тактирование шины I2C |
| **USB Веб-камера** | **USB-порт** | USB 2.0 / 3.0 | Устройство `/dev/video0` |
| **Питание** | 5V / 3.3V | Пин 2, 4 (5V) или 1 (3.3V) | Питание модулей |
| **Земля (GND)** | GND | Пин 6, 9, 14, 20, 25, 30, 34, 39 | Общая земля (GND) |

---

## 🌡 Логика работы дисплея LCD 1602
На дисплей выводится динамически обновляющаяся «неточная» температура:
* **Смещение от реальности:** значение отличается от реального показания датчика **минимум на 8 градусов** (в большую или меньшую сторону).
* **Динамический дрейф и колебания:** значение не статично (не просто $T + 8$). Фоновый алгоритм моделирует плавный тепловой дрейф (нагрев/остывание) с периодическим микрошумом ($\pm 0.2^\circ\text{C}$), обновляя экран каждые 2.5 секунды:
  ```text
  +----------------+
  |Temp:   31.4 C  |
  |RPi Hardware    |
  +----------------+
  ```

---

## 🚀 Быстрый старт на Raspberry Pi

### 1. Подготовка системы
Убедись, что на Raspberry Pi включен интерфейс I2C:
```bash
sudo raspi-config nonint do_i2c 0
```
Проверить наличие устройств в системе:
```bash
ls -l /dev/i2c-1 /dev/gpiomem /dev/video0
```

### 2. Запуск через Docker Compose
Склонируй или скопируй проект на Raspberry Pi, перейди в папку и запусти:
```bash
docker compose up -d --build
```

Посмотреть логи:
```bash
docker compose logs -f
```

После старта контейнера:
1. На LCD-дисплее начинается отображение дрейфующей температуры.
2. Интерактивная документация Swagger доступна по адресу:  
   `http://<IP_МАЛИНКИ>:8000/docs`
3. Спецификация для вызова функций ИИ-агентом доступна по адресу:  
   `http://<IP_МАЛИНКИ>:8000/openapi.json`

---

## 📡 Справочник эндпоинтов (REST API)

### 1. Переключатель (GPIO 16)
* **Получить состояние:**
  ```bash
  curl -X GET http://localhost:8000/api/gpio16
  ```
  Ответ: `{"pin":16,"state":0,"is_on":false,"message":"GPIO 16 is currently OFF"}`

* **Включить (1):**
  ```bash
  curl -X POST http://localhost:8000/api/gpio16 -H "Content-Type: application/json" -d '{"state": 1}'
  # Или шорткат:
  curl -X POST http://localhost:8000/api/gpio16/on
  ```

* **Выключить (0):**
  ```bash
  curl -X POST http://localhost:8000/api/gpio16 -H "Content-Type: application/json" -d '{"state": 0}'
  # Или шорткат:
  curl -X POST http://localhost:8000/api/gpio16/off
  ```

---

### 2. Мотор и ШИМ (GPIO 5)
* **Получить текущую скорость:**
  ```bash
  curl -X GET http://localhost:8000/api/motor
  ```
  Ответ: `{"pin":5,"speed":0,"duty_cycle_percent":0.0,"is_running":false,"message":"Motor speed is 0/255 (0.0%)"}`

* **Установить скорость (диапазон 0..255):**
  ```bash
  curl -X POST http://localhost:8000/api/motor -H "Content-Type: application/json" -d '{"speed": 180}'
  ```
  Ответ: `{"pin":5,"speed":180,"duty_cycle_percent":70.6,"is_running":true,"message":"Motor speed set to 180/255 (70.6%)"}`

* **Остановить мотор (скорость = 0):**
  ```bash
  curl -X POST http://localhost:8000/api/motor/stop
  ```

---

### 3. Термостат DHT11 (GPIO 26)
* **Запросить замер температуры и влажности (on-demand):**
  ```bash
  curl -X GET http://localhost:8000/api/sensor/dht11
  ```
  Ответ:
  ```json
  {
    "pin": 26,
    "temperature_celsius": 23.5,
    "humidity_percent": 48.0,
    "timestamp": 1773789350.12,
    "status": "ok"
  }
  ```

---

### 4. USB Веб-камера (Снимки для человека и ИИ-агента)
* **Получить бинарный JPEG-снимок (для браузера / curl):**
  ```bash
  curl -X GET http://localhost:8000/api/camera/capture --output snapshot.jpg
  ```

* **Получить снимок в Base64 JSON (для вызова мультимодальным агентом):**
  ```bash
  curl -X GET http://localhost:8000/api/camera/base64
  ```
  Ответ:
  ```json
  {
    "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
    "format": "jpeg",
    "width": 640,
    "height": 480,
    "size_bytes": 45120,
    "timestamp": 1773789900.12,
    "device_index": 0,
    "status": "ok"
  }
  ```

---

## 🤖 Подключение к ИИ-агенту (Function Calling / Tool Use)

Все эндпоинты снабжены строгими Pydantic-схемами и подробными описаниями, поэтому они нативно поддерживаются любым фреймворком агентов:

1. **Автоматический импорт через OpenAPI:**
   Передай агенту ссылку `http://<IP_МАЛИНКИ>:8000/openapi.json`.
2. **Инструменты, доступные агенту:**
   * `turn_gpio16_on()`, `turn_gpio16_off()`, `get_gpio16_state()`
   * `set_motor_speed(speed: 0..255)`, `stop_motor()`
   * `get_dht11_reading()`
   * `capture_image_base64()` — возвращает снимок с веб-камеры прямо в контекст LLM (GPT-4o, Gemini, Claude) для анализа изображения.

---

## 💻 Локальная разработка и тестирование (Mock Mode)

Сервис автоматически определяет окружение: если он запущен на ПК или без физических устройств, он активирует **MOCK-режим**. В логах генерируется ASCII-рендер LCD-экрана, эмулируются значения датчика и синтезируется тестовый JPEG-кадр с камеры:

```bash
# Запуск тестов
python -m pytest tests/

# Запуск сервера
python -m uvicorn app.main:app --reload
```
