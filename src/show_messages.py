import paho.mqtt.client as mqtt
import json
from datetime import datetime

# --- SETTINGS ---
MQTT_BROKER = "192.168.1.100"
MQTT_PORT = 1883
MQTT_TOPIC = "home/sniffers"


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"✅ Connected to Mosquitto")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"❌ Connection failed: {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        sensor = payload.get("sensor", "Unknown")
        vcc = payload.get("vcc", "Unknown")
        devices = payload.get("data", [])

        print(f"\n📡 Sensor: [{sensor}] vcc={vcc/1000}V reported {len(devices)} devices")
        
        # Sort by signal strength (strongest first)
        sorted_devices = sorted(devices, key=lambda x: x['r'], reverse=True)

        for dev in sorted_devices[:10]: # Show top 10
            rssi = dev['r']
            # Color code for signal strength (terminal only)
            color = "\033[92m" if rssi > -60 else "\033[93m" if rssi > -80 else "\033[91m"
            print(f"  {color}MAC: {dev['m']} | RSSI: {rssi}dBm\033[0m")

    except Exception as e:
        print(f"Error: {e}")

# Use Callback Version 2 for newer paho-mqtt
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

print(f"Connecting to {MQTT_BROKER}...")
client.connect(MQTT_BROKER, MQTT_PORT)
client.loop_forever()