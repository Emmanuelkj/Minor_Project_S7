# Thalir IoT — Smart Agriculture & AI Plant Health Platform

An end-to-end Smart Agriculture IoT system integrating an **ESP32 microcontroller (MicroPython)**, a **FastAPI backend with a genuine MobileNetV2 deep learning model**, and a **React 18 / Tailwind CSS web dashboard**.

---

## 🌟 System Architecture

```
+-----------------------------------+
|     ESP32 Microcontroller         |
| - MicroPython Firmware            |
| - DHT11 Sensor (GPIO 4)           |
| - Soil Moisture Sensor (GPIO 34)  |
| - Physical Alert LED (GPIO 2)     |
| - REST API: http://thalir.local   |
+-----------------------------------+
                 │
           Wi-Fi / mDNS
                 ▼
+-----------------------------------+        HTTP / REST        +-----------------------------------+
|      FastAPI Backend Server       |  <=====================>  |       React Web Dashboard         |
| - REST API on port 8000           |                           | - Vite + React 18 + Tailwind CSS  |
| - SQLite Database (thalir.db)     |                           | - Real-time Telemetry Gauges      |
| - MobileNetV2 AI Model (PyTorch)  |                           | - Interactive AI Leaf Scanner     |
| - 38 Agricultural Disease Classes |                           | - Automated Alert Dispatch to LED |
+-----------------------------------+                           +-----------------------------------+
```

---

## 📁 Project Directory Structure

```text
Minor-ProjecT-IoT/
├── ai-model/
│   ├── inference.py            # MobileNetV2 inference engine (PyTorch)
│   ├── disease_db.py           # 38 plant disease agronomic knowledge base
│   ├── mobilenetv2_plant.pth   # Pre-trained deep learning weights (PlantVillage, 95% acc)
│   ├── sample_images/          # Sample healthy and diseased test leaves
│   └── train.py                # MobileNetV2 transfer learning training pipeline
├── backend/
│   ├── main.py                 # FastAPI application entry point
│   ├── database.py             # SQLite / SQLAlchemy connection
│   ├── models.py & schemas.py  # Database ORM models and Pydantic schemas
│   ├── routers/                # API routes (predict, sensors, plants, alerts, reports)
│   └── requirements.txt        # Python backend dependencies
├── esp32/
│   ├── esp32_sensor_node.ino   # Original Arduino C++ sketch (reference)
│   └── micropython/
│       ├── boot.py             # Wi-Fi auto-connect & thalir.local mDNS setup
│       ├── main.py             # Hardware sensor loop & REST API (port 80)
│       ├── esp32-firmware.bin  # Official ESP32 MicroPython firmware binary
│       └── README.md           # Step-by-step flashing & ampy recovery guide
├── frontend/
│   ├── src/                    # React components, pages, and UI styles
│   ├── vite.config.js          # Vite config with thalir.local proxy
│   ├── package.json            # React dependencies
│   └── dist/                   # Compiled production build
└── raspberry-pi/               # Optional Raspberry Pi camera and sensor nodes
```

---

## ⚡ Quick Start Guide (Run the Project)

### Step 1: ESP32 Hardware & MicroPython Setup

1. **Hardware Wiring**:
   - **DHT11 Data** $\rightarrow$ **GPIO 4**
   - **Soil Moisture AO** $\rightarrow$ **GPIO 34**
   - **Alert LED** $\rightarrow$ **GPIO 2**
   - **Power & GND** $\rightarrow$ **3.3V / GND**

2. **Flash MicroPython (First Time Only)**:
   ```bash
   pip install esptool adafruit-ampy
   esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
   esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 esp32/micropython/esp32-firmware.bin
   ```

3. **Configure Wi-Fi & Upload Code**:
   - Open `esp32/micropython/boot.py` and set your Wi-Fi name & password:
     ```python
     WIFI_SSID = "Your_WiFi_Name"
     WIFI_PASSWORD = "Your_WiFi_Password"
     ```
   - Upload both files to the ESP32:
     ```bash
     cd esp32/micropython
     ampy --port /dev/ttyUSB0 put boot.py
     ampy --port /dev/ttyUSB0 put main.py
     ampy --port /dev/ttyUSB0 reset
     ```
   *(Your ESP32 is now accessible on your local network at `http://thalir.local`)*.

> [!TIP]
> **To retrieve your files from the ESP32 if you ever lose them:**
> ```bash
> ampy --port /dev/ttyUSB0 get main.py > main.py
> ampy --port /dev/ttyUSB0 get boot.py > boot.py
> ```

---

### Step 2: Start the FastAPI Backend (AI Model & API)

In a new terminal window:
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
*(The backend will start at `http://127.0.0.1:8000` and load the pre-trained `mobilenetv2_plant.pth` model).*

---

### Step 3: Start the React Web Frontend

In another terminal window:
```bash
cd frontend
npm install
npm run dev
```
Open **`http://localhost:5173`** in your browser.

---

## 🌿 Live Features

1. **Real-Time Environmental Telemetry**:
   - Air Temperature (°C) and Humidity (%) from physical DHT11.
   - Soil Moisture (%) and 12-bit ADC raw readout from Pin 34.
   - Polled live every 3 seconds directly from `http://thalir.local/api/data`.

2. **MobileNetV2 AI Leaf Disease Scanner**:
   - Upload any leaf photo (or choose from `ai-model/sample_images/`).
   - The deep convolutional neural network diagnoses the plant condition across 38 crop categories.
   - Provides confidence score, symptoms, causes, organic treatments, and chemical remedies.

3. **Automated Hardware Alert Dispatch**:
   - When the AI detects an infected or diseased leaf, the platform automatically calls the ESP32 API (`/api/command?cmd=BAD`), triggering the **physical alert LED on GPIO 2 to turn ON**.
