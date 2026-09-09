import os,json,asyncio
import paho.mqtt.client as mqtt

def connect(loop, ingest, storage):
    if not os.getenv('MQTT_HOST'): return None
    client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if os.getenv('MQTT_USERNAME'): client.username_pw_set(os.getenv('MQTT_USERNAME'),os.getenv('MQTT_PASSWORD'))
    if os.getenv('MQTT_TLS','false').lower()=='true': client.tls_set()
    def on_connect(c,u,f,rc,p):
        if rc==0: c.subscribe(os.getenv('MQTT_TOPIC','neela/telemetry'))
    def on_message(c,u,m):
        async def handle():
            try: await ingest(json.loads(m.payload),'WOKWI')
            except Exception as e: storage.event('INGEST REJECTED',str(e)[:200])
        asyncio.run_coroutine_threadsafe(handle(),loop)
    client.on_connect=on_connect;client.on_message=on_message
    client.connect_async(os.getenv('MQTT_HOST'),int(os.getenv('MQTT_PORT','1883')));client.loop_start();return client
