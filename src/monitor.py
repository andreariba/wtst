import os
from dotenv import load_dotenv, find_dotenv
import paho.mqtt.client as mqtt
import json
import psycopg2
import psycopg2.pool
from psycopg2.extras import execute_values
from datetime import datetime

load_dotenv(find_dotenv())

# --- SETTINGS ---
MQTT_BROKER = "192.168.1.100"
MQTT_PORT = 1883
MQTT_TOPIC = "home/sniffers"

# Database URL
DB_URL = os.getenv("DB_URL")
print(DB_URL)

# --- DATABASE SETUP ---
try:
    db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DB_URL)
    print("✅ Connected to PostgreSQL Pool")
except Exception as e:
    print(f"❌ Database Connection Error: {e}")
    exit(1)

def init_db():
    conn = db_pool.getconn()
    cur = conn.cursor()
    # Added vcc column (storing as INTEGER to keep millivolts)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rssi_signals.sniffer_data (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP,
            sensor_id VARCHAR(50),
            vcc INTEGER,
            mac_address VARCHAR(20),
            rssi INTEGER
        )
    """)
    conn.commit()
    cur.close()
    db_pool.putconn(conn)
    print("✅ Table 'rssi_signals.sniffer_data'.")

# --- MQTT CALLBACKS ---
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"✅ Connected to Mosquitto")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"❌ MQTT Connection failed: {rc}")

def on_message(client, userdata, msg):
    conn = None
    try:
        payload = json.loads(msg.payload.decode())
        sensor_id = payload.get("sensor", "Unknown")
        vcc = payload.get("vcc", 0) # Get the battery voltage
        timestamp = datetime.now()
        devices = payload.get("data", [])

        if not devices:
            return

        # Prepare data: adding 'vcc' to every row for this sensor report
        values = [(timestamp, sensor_id, vcc, d["m"], d["r"]) for d in devices]

        # Get connection from pool and insert
        conn = db_pool.getconn()
        cur = conn.cursor()
        query = """
            INSERT INTO rssi_signals.sniffer_data (timestamp, sensor_id, vcc, mac_address, rssi) 
            VALUES %s
        """
        execute_values(cur, query, values)
        
        conn.commit()
        cur.close()
        db_pool.putconn(conn)
        
        print(f"[{timestamp.strftime('%H:%M:%S')}] {sensor_id} ({vcc}mV): Saved {len(devices)} devices.")

    except Exception as e:
        print(f"❌ Error: {e}")
        if conn:
            db_pool.putconn(conn)

# --- EXECUTION ---
init_db()

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

print(f"Connecting to MQTT Broker at {MQTT_BROKER}...")
try:
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.loop_forever()
except KeyboardInterrupt:
    print("\nStopping script...")
except Exception as e:
    print(f"❌ Critical Error: {e}")