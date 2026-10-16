# ESP32 MicroPython Plant Health Monitor & Web Dashboard

Pure MicroPython code for the ESP32 Plant Health Monitor converted from Arduino and the Minor-ProjecT-IoT dashboard.

---

## Files

- [`boot.py`](file:///home/docx/Minor-ProjecT-IoT/esp32/micropython/boot.py): Handles Wi-Fi connection (Station mode, with automatic Access Point fallback to `Thalir-ESP32`).
- [`main.py`](file:///home/docx/Minor-ProjecT-IoT/esp32/micropython/main.py): All project logic (DHT11, Soil ADC, LED on/off alerts, serial command listener, and complete embedded web server + dashboard).

---

## Hardware Pin Connections

- **DHT11 Data** -> **GPIO 4**
- **Soil Moisture AO** -> **GPIO 34**
- **Alert LED** -> **GPIO 2**
- **VCC** -> **3.3V**
- **GND** -> **GND**

---

## Uploading to ESP32 with Ampy

```bash
cd esp32/micropython

# Upload both files:
ampy --port /dev/ttyUSB0 put boot.py
ampy --port /dev/ttyUSB0 put main.py

# Soft reboot the board:
ampy --port /dev/ttyUSB0 reset
```
*(On Windows, replace `/dev/ttyUSB0` with your COM port, e.g. `COM3`)*

---

## How to Retrieve / Recover Your Files If You Lose Them

Because MicroPython stores the code on the ESP32's flash memory, you can download the exact files back to your computer at any time using `ampy`:

```bash
# 1. See what files are on your ESP32:
ampy --port /dev/ttyUSB0 ls

# 2. Retrieve main.py:
ampy --port /dev/ttyUSB0 get main.py > main.py

# 3. Retrieve boot.py:
ampy --port /dev/ttyUSB0 get boot.py > boot.py
```

---

## How to View the Web Dashboard

When the ESP32 boots, it prints its IP address to the serial monitor:
- If connected to your Wi-Fi router, open `http://<ESP32_IP>/` in any browser.
- If standalone, connect to the ESP32's Wi-Fi hotspot (`Thalir-ESP32`) and open `http://192.168.4.1/`.
