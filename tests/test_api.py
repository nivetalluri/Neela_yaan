"""Separate integration run: python tests/test_api.py (isolated temporary DB)."""
import tempfile,os,sys,asyncio
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
def run():
 from fastapi.testclient import TestClient
 with tempfile.TemporaryDirectory() as tmp:
  os.environ['DATABASE_PATH']=tmp+'/integration.sqlite3'
  os.environ['TELEMETRY_SOURCE']='WOKWI'
  os.environ['INGEST_TOKEN']='test-only-not-a-deployment-secret'
  from backend.main import app
  from backend.simulator import sample
  with TestClient(app) as c:
   assert c.get('/api/health').status_code==200
   with c.websocket_connect('/ws') as ws:
    p=sample(0,{})
    assert c.post('/api/telemetry',json=p).status_code==401
    assert c.post('/api/telemetry',json=p,headers={'X-Ingest-Token':os.environ['INGEST_TOKEN']}).status_code==200
    m=ws.receive_json();assert m['type']=='telemetry' and m['data']['source']=='WOKWI'
    assert c.post('/api/telemetry',json=p,headers={'X-Ingest-Token':os.environ['INGEST_TOKEN']}).status_code==409
    assert c.post('/api/control/fail_gps').status_code==409
    ws.send_text('ping');assert ws.receive_json()['type']=='heartbeat'
   assert len(c.get('/api/history').json())==1
   assert 'ocean.temperature' in c.get('/api/export').text
   for section in ['ocean','atmosphere','navigation','waves','power','mission','ice']:
    assert c.get('/api/'+section).status_code==200
   assert c.post('/api/control/pause').json()['running']==False
  print('PASS: authenticated HTTP ingress, WebSocket delivery, heartbeat, duplicate rejection, source isolation, subsystem APIs, CSV, history and pause.')

if __name__=="__main__":run()
