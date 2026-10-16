# ==============================================================================
# boot.py - Wi-Fi Connection & mDNS Hostname Setup for ESP32
# ==============================================================================

import gc
import network
import time

gc.enable()
gc.collect()

# Set your Wi-Fi credentials here
WIFI_SSID = "Thalir"
WIFI_PASSWORD = "12345678"
HOSTNAME = "thalir"

def connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    # Set hostname so it is accessible via http://thalir.local
    try:
        network.hostname(HOSTNAME)
    except Exception:
        pass
    try:
        wlan.config(dhcp_hostname=HOSTNAME)
    except Exception:
        pass

    if WIFI_SSID and WIFI_SSID != "YOUR_WIFI_SSID":
        print("[Wi-Fi] Connecting to", WIFI_SSID, "...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        start = time.time()
        while not wlan.isconnected() and (time.time() - start) < 15:
            time.sleep(0.5)
            print(".", end="")
        print()

    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        print("\n[Wi-Fi] Connected successfully!")
        print("[Wi-Fi] Assigned IP Address :", ip)
        print("[Web Dashboard] Access via : http://thalir.local")
        print("[Web Dashboard] Or direct IP: http://" + ip)
        return ip
    else:
        # Fallback to Access Point if router Wi-Fi is not reachable
        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        ap.config(essid="Thalir-ESP32", authmode=network.AUTH_OPEN)
        ap_ip = ap.ifconfig()[0]
        print("\n[Wi-Fi AP] Fallback hotspot: 'Thalir-ESP32'")
        print("[Web Dashboard] Connect to hotspot and open: http://" + ap_ip)
        return ap_ip

connect()
gc.collect()
