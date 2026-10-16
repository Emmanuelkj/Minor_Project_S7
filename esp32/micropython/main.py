# ==============================================================================
# main.py - ESP32 MicroPython Sensor & REST API Node (Clean API Mode)
# ==============================================================================

import machine
import dht
import time
import sys
import select
import socket
import gc
try:
    import ujson as json
except ImportError:
    import json

# --- 1. HARDWARE PINS ---
DHTPIN = 4
SOIL_PIN = 34
LED_PIN = 2

led = machine.Pin(LED_PIN, machine.Pin.OUT)
led.value(0)

dht_sensor = dht.DHT11(machine.Pin(DHTPIN))

soil_adc = machine.ADC(machine.Pin(SOIL_PIN))
try:
    soil_adc.atten(machine.ADC.ATTN_11DB)
    soil_adc.width(machine.ADC.WIDTH_12BIT)
except AttributeError:
    pass

# --- 2. TIMING & STATE ---
SENSOR_INTERVAL = 2000
ALERT_DURATION = 5000

lastSensorRead = 0
badLeafAlertActive = False
alertStartTime = 0

latest_temp = 25.0
latest_hum = 60.0
latest_soil_raw = 2000
latest_soil_pct = 50.0
dht_ok = False

# Non-blocking USB Serial listener
spoll = select.poll()
spoll.register(sys.stdin, select.POLLIN)


# --- 3. HARDWARE CONTROL FUNCTIONS ---

def set_alert(active: bool):
    global badLeafAlertActive, alertStartTime
    badLeafAlertActive = active
    if active:
        alertStartTime = time.ticks_ms()
        led.value(1)
        print("ALERT: BAD LEAF DETECTED")
        print("LED: ON")
    else:
        led.value(0)
        print("STATUS: HEALTHY LEAF")
        print("LED: OFF")


def check_serial():
    if spoll.poll(0):
        try:
            line = sys.stdin.readline().strip().upper()
            if line in ("BAD", "ALERT"):
                set_alert(True)
            elif line in ("GOOD", "OK"):
                set_alert(False)
        except Exception:
            pass


def check_alert_timeout(now):
    global badLeafAlertActive
    if badLeafAlertActive and time.ticks_diff(now, alertStartTime) >= ALERT_DURATION:
        badLeafAlertActive = False
        led.value(0)
        print("Alert timeout - LED OFF")


def read_sensors():
    global latest_temp, latest_hum, latest_soil_raw, latest_soil_pct, dht_ok

    # Read Soil Moisture ADC (3200 dry -> 1300 wet)
    try:
        latest_soil_raw = soil_adc.read()
        latest_soil_pct = max(0.0, min(100.0, ((3200 - latest_soil_raw) * 100.0) / 1900.0))
    except Exception:
        pass

    # Read DHT11
    try:
        dht_sensor.measure()
        latest_temp = float(dht_sensor.temperature())
        latest_hum = float(dht_sensor.humidity())
        dht_ok = True
    except Exception:
        dht_ok = False

    if not dht_ok:
        print("ERROR: DHT11 reading failed!")
    else:
        led_str = "ON" if led.value() == 1 else "OFF"
        print("DATA | Temp: {:.1f} C | Humidity: {:.1f} % | Soil Raw: {} | LED: {}".format(
            latest_temp, latest_hum, latest_soil_raw, led_str
        ))


# --- 4. LIGHTWEIGHT REST API SERVER (PORT 80) ---

CORS_HEADERS = (
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: application/json\r\n"
    "Access-Control-Allow-Origin: *\r\n"
    "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
    "Access-Control-Allow-Headers: Content-Type\r\n"
    "Connection: close\r\n\r\n"
)

def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 80))
    s.listen(3)
    s.setblocking(False)
    return s


def handle_client(client):
    try:
        req = client.readline().decode('utf-8', 'ignore')
        if not req:
            client.close()
            return
        parts = req.split(' ')
        if len(parts) < 2:
            client.close()
            return

        method = parts[0]
        path = parts[1]

        # Flush rest of HTTP request headers
        while True:
            h = client.readline()
            if not h or h == b'\r\n' or h == b'\n':
                break

        # Handle CORS preflight OPTIONS request
        if method == "OPTIONS":
            client.write(CORS_HEADERS.encode('utf-8'))
            client.close()
            return

        # API: /api/data or /api/v1/sensors/live
        if '/api/data' in path or '/sensors/live' in path:
            payload = json.dumps({
                "temperature": round(latest_temp, 1),
                "humidity": round(latest_hum, 1),
                "soil_raw": latest_soil_raw,
                "soil_moisture": round(latest_soil_pct, 1),
                "light_lux": 820.0,
                "led": "ON" if led.value() == 1 else "OFF",
                "alert_active": badLeafAlertActive,
                "health_status": "Diseased Leaf Alert" if badLeafAlertActive else "Healthy",
                "device": "ESP32 Thalir Node"
            })
            client.write(CORS_HEADERS.encode('utf-8'))
            client.write(payload.encode('utf-8'))

        # API: /api/command?cmd=BAD or GOOD
        elif '/api/command' in path:
            cmd = ""
            if 'cmd=' in path:
                cmd = path.split('cmd=')[1].split('&')[0].upper()
            if cmd in ("BAD", "ALERT"):
                set_alert(True)
            elif cmd in ("GOOD", "OK"):
                set_alert(False)

            payload = json.dumps({
                "status": "success",
                "command": cmd,
                "led": "ON" if led.value() == 1 else "OFF",
                "alert_active": badLeafAlertActive
            })
            client.write(CORS_HEADERS.encode('utf-8'))
            client.write(payload.encode('utf-8'))

        # Default info endpoint for /
        elif path == '/':
            payload = json.dumps({
                "service": "Thalir ESP32 REST API Node",
                "endpoints": ["/api/data", "/api/command?cmd=BAD", "/api/command?cmd=GOOD"],
                "status": "online"
            })
            client.write(CORS_HEADERS.encode('utf-8'))
            client.write(payload.encode('utf-8'))

        else:
            client.write(b"HTTP/1.1 404 Not Found\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n")

    except Exception:
        pass
    finally:
        try:
            client.close()
        except Exception:
            pass


# --- 5. MAIN SUPER-LOOP ---

def main():
    print("==========================================")
    print("ESP32 REST API SENSOR NODE (MicroPython)")
    print("==========================================")
    print("DHT11      -> GPIO 4")
    print("Soil AO    -> GPIO 34")
    print("LED        -> GPIO 2")
    print("REST API   -> http://thalir.local/api/data")
    print("==========================================")

    server = start_server()
    global lastSensorRead
    lastSensorRead = time.ticks_ms()
    read_sensors()

    while True:
        now = time.ticks_ms()

        # 1. Check serial command from Python / USB
        check_serial()

        # 2. Check 5-second alert timeout
        check_alert_timeout(now)

        # 3. Read sensors every 2 seconds
        if time.ticks_diff(now, lastSensorRead) >= SENSOR_INTERVAL:
            lastSensorRead = now
            read_sensors()
            gc.collect()

        # 4. Handle incoming REST API requests
        try:
            cl, _ = server.accept()
            handle_client(cl)
        except OSError:
            pass

        time.sleep_ms(20)


if __name__ == "__main__":
    main()
