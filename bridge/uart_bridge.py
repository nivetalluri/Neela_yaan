"""Forward NEW line-delimited STM32 UART frames over HTTP or MQTT.
UTC timestamp is gateway receipt time: the demo STM32 has no RTC.
Never relabel an archived logfile as a live run.
"""
import argparse,json,os,time,sys,urllib.request
from datetime import datetime,timezone
from dotenv import load_dotenv
load_dotenv()
p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
g.add_argument('--serial',help='Physical serial port, e.g. /dev/ttyACM0')
g.add_argument('--follow',help='Actively appended Wokwi CLI UART logfile (starts at EOF)')
p.add_argument('--backend',default='http://127.0.0.1:8000');p.add_argument('--mqtt',action='store_true');p.add_argument('--baud',type=int,default=115200)
a=p.parse_args();client=None
if a.mqtt:
 import paho.mqtt.client as mqtt
 client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
 if os.getenv('MQTT_USERNAME'):client.username_pw_set(os.getenv('MQTT_USERNAME'),os.getenv('MQTT_PASSWORD'))
 if os.getenv('MQTT_TLS','false').lower()=='true':client.tls_set()
 client.connect(os.environ['MQTT_HOST'],int(os.getenv('MQTT_PORT','1883')));client.loop_start()
if a.serial:
 import serial
 stream=serial.Serial(a.serial,a.baud,timeout=1)
else:
 stream=open(a.follow,'rb');stream.seek(0,2)
pending=b''
while True:
 raw=stream.readline()
 if not raw:time.sleep(.05);continue
 pending+=raw
 if not pending.endswith(b'\n'):continue
 raw=pending;pending=b''
 try:
  # Accept complete JSON lines only; ignore startup banners and diagnostics.
  d=json.loads(raw.decode().strip())
  d['timestamp']=datetime.now(timezone.utc).isoformat()
  packet=json.dumps(d).encode()
  if client:
   result=client.publish(os.getenv('MQTT_TOPIC','neela/telemetry'),packet,qos=1);result.wait_for_publish(timeout=10)
  else:
   req=urllib.request.Request(a.backend.rstrip('/')+'/api/telemetry',packet,{'Content-Type':'application/json','X-Ingest-Token':os.environ['INGEST_TOKEN']},method='POST')
   with urllib.request.urlopen(req,timeout=10) as response:response.read()
  print('Forwarded UART frame:',d['timestamp'],flush=True)
 except (ValueError,UnicodeError): print('Ignored non-JSON UART line',file=sys.stderr)
 except Exception as e: print('Forward failed (not queued by bridge):',e,file=sys.stderr)
