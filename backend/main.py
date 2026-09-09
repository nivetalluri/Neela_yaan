import asyncio,os,time,secrets,csv,io,math,json
from contextlib import asynccontextmanager
from datetime import datetime,timezone
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI,WebSocket,HTTPException,Header,Query
from fastapi.responses import Response
from .telemetry_models import Telemetry
from .data_processor import Processor
from .mission_manager import MissionManager,now
from .ice_algorithm import evaluate
from .storage import Storage
from .communication_manager import CommunicationManager
from .websocket_manager import WebsocketManager
from .simulator import sample
from .mqtt_client import connect
from .report_manager import ReportManager

storage=Storage();processor=Processor();mission=MissionManager();comm=CommunicationManager(storage);ws=WebsocketManager()
reports=ReportManager(storage)
SAMPLE_INTERVAL=7.0
latest=(storage.history(1) or [None])[0]
storage.db.execute('CREATE TABLE IF NOT EXISTS simulator_state(id INTEGER PRIMARY KEY CHECK(id=1),tick REAL NOT NULL)')
storage.db.execute('INSERT OR IGNORE INTO simulator_state(id,tick) VALUES(1,0)');storage.db.commit()
source=os.getenv('TELEMETRY_SOURCE','DEMO'); running=True; faults={}; tick=storage.db.execute('SELECT tick FROM simulator_state WHERE id=1').fetchone()[0]; lock=asyncio.Lock(); last_received=None; mqtt=None
pending_external=None;external_last_timestamp=None
stages=['SENSOR SAMPLE ACQUIRED','DATA VALIDATED','DATA PROCESSED','GPS POSITION RECEIVED','ICE ALGORITHM EXECUTED','MISSION LOGIC EVALUATED','DATA STORED']
async def ingest(payload,origin,scheduled=False):
    global latest,last_received,pending_external,external_last_timestamp
    if origin!=source: raise ValueError('Source mismatch; choose matching acquisition source first')
    if not running: raise ValueError('Mission is paused')
    validated=Telemetry.model_validate(payload).model_dump(mode='json')
    validated['timestamp']=datetime.fromisoformat(validated['timestamp'].replace('Z','+00:00')).astimezone(timezone.utc).isoformat()
    age=abs((datetime.now(timezone.utc)-datetime.fromisoformat(validated['timestamp'])).total_seconds())
    if age>30: raise ValueError('Telemetry timestamp outside 30-second live window')
    if origin=='WOKWI' and not scheduled:
        if external_last_timestamp and validated['timestamp']<=external_last_timestamp: raise ValueError('Out-of-order or duplicate telemetry')
        # Latest-frame buffer: the recording scheduler consumes it once per 7-second slot.
        # Faster incoming frames are intentionally coalesced, never double-recorded.
        external_last_timestamp=validated['timestamp'];pending_external=validated
        return {'accepted':True,'recorded':False,'status':'QUEUED FOR NEXT 7-SECOND RECORDING SLOT'}
    async with lock:
        if latest and latest.get('source')==origin and validated['timestamp']<=latest['timestamp']: raise ValueError('Out-of-order or duplicate telemetry')
        d=processor.process(validated); d['source']=origin;d['received_at']=now()
        ice=evaluate(d); d['ice']=ice;d['mission'],changed=mission.evaluate(d,ice)
        for stage in stages[:-1]:
            if stage!='GPS POSITION RECEIVED' or d['navigation']['gps_fix']: storage.event(stage,origin)
        if changed: storage.event('MISSION STATE CHANGED',d['mission']['state']+' • '+d['mission']['reason'])
        invalid=[k for k,v in d['quality'].items() if v in ('INVALID','MISSING')]
        if invalid: storage.event('FAULT DETECTED',', '.join(invalid))
        id=storage.save(d);storage.event('DATA STORED',f'SQLite sample #{id}')
        d['communication'].update(comm.transmit(d['communication']['satellite_status']=='CONNECTED'))
        d['id']=id;d['pipeline']=[{'name':s,'timestamp':now(),'status':'WARNING' if invalid and s=='DATA VALIDATED' else 'GOOD','errors':len(invalid) if s=='DATA VALIDATED' else 0} for s in stages]
        storage.update(id,d);latest=d;last_received=time.monotonic()
        await ws.broadcast({'type':'telemetry','data':d,'events':storage.events()[:30]})
async def simulate():
    global tick,pending_external
    loop=asyncio.get_running_loop();deadline=loop.time()
    # Monotonic deadline scheduling avoids adding processing time to every interval.
    while True:
        await asyncio.sleep(max(0,deadline-loop.time()))
        if running and source=='DEMO':
            tick+=SAMPLE_INTERVAL;d=sample(tick,faults)
            if faults.get('sensor'): d['ocean']['temperature']=999
            try:
                await ingest(d,'DEMO')
                storage.db.execute('UPDATE simulator_state SET tick=? WHERE id=1',(tick,));storage.db.commit()
            except Exception as e: storage.event('ACQUISITION ERROR',str(e)[:200])
        elif running and source=='WOKWI' and pending_external is not None:
            frame=pending_external;pending_external=None
            try: await ingest(frame,'WOKWI',scheduled=True)
            except Exception as e: storage.event('EXTERNAL SAMPLE REJECTED',str(e)[:200])
        deadline+=SAMPLE_INTERVAL
        if deadline<loop.time():
            skipped=math.ceil((loop.time()-deadline)/SAMPLE_INTERVAL)
            deadline+=skipped*SAMPLE_INTERVAL
            storage.event('SAMPLING DEADLINE MISSED',f'{skipped} slots skipped; no fabricated backfill')
def report_job(method,*args):
    # A dedicated WAL connection keeps large 10-day aggregation off the acquisition loop.
    connection=Storage()
    try: return getattr(ReportManager(connection),method)(*args)
    finally: connection.db.close()
async def report_scheduler():
    while True:
        try:
            ids=await asyncio.to_thread(report_job,'run_due')
            if ids: await ws.broadcast({'type':'report','ids':ids,'schedule':reports.status()})
        except Exception as e: storage.event('REPORT SCHEDULER ERROR',str(e)[:200])
        await asyncio.sleep(30)
@asynccontextmanager
async def lifespan(app):
    global mqtt
    storage.event('MISSION STARTED','Demo software controller; no real hardware attached')
    mqtt=connect(asyncio.get_running_loop(),ingest,storage)
    task=asyncio.create_task(simulate());report_task=asyncio.create_task(report_scheduler())
    yield
    task.cancel();report_task.cancel()
    await asyncio.gather(task,report_task,return_exceptions=True)
    if mqtt: mqtt.loop_stop();mqtt.disconnect()
app=FastAPI(title='Neela Yaan Telemetry',lifespan=lifespan)
@app.get('/api/health')
def health(): return {'status':'ok','source':source,'running':running,'faults':faults,'mqtt_configured':bool(mqtt),'mqtt_connected':mqtt.is_connected() if mqtt else False,'last_packet_age':None if last_received is None else time.monotonic()-last_received,'storage':storage.counts(),'server_utc':now(),'sample_interval_seconds':7,'report_schedule':reports.status()}

@app.get('/api/time')
def clock():
    return {'server_utc':now(),'unix_ms':time.time()*1000,'timezone':'UTC','sample_interval_seconds':7,'clock_basis':'Server system clock. Host NTP/GNSS synchronization required for absolute accuracy.'}
@app.get('/api/reports')
async def report_list(): return {'reports':reports.list(),'schedule':reports.status()}
@app.post('/api/reports/preview')
async def report_preview():
    result=await asyncio.to_thread(report_job,'preview')
    await ws.broadcast({'type':'report','ids':[result['id']],'schedule':reports.status()})
    return result
@app.get('/api/reports/{report_id}')
async def report_detail(report_id:int):
    result=reports.get(report_id)
    if not result: raise HTTPException(404,'Report not found')
    return result
@app.post('/api/reports/{report_id}/read')
async def report_read(report_id:int):
    if not reports.get(report_id): raise HTTPException(404,'Report not found')
    reports.read(report_id);return {'read':True}
@app.get('/api/reports/{report_id}/download')
async def report_download(report_id:int,format:str='json'):
    result=reports.get(report_id)
    if not result: raise HTTPException(404,'Report not found')
    if format=='csv':
        out=io.StringIO();w=csv.writer(out)
        w.writerow(['report_id','kind','period_start_utc','period_end_utc','sources','parameter','unit','minimum','maximum','average','valid_samples'])
        for path,m in result['metrics'].items():w.writerow([report_id,result['kind'],result['period_start'],result['period_end'],' / '.join(result['sources']),path,m['unit'],m['min'],m['max'],m['mean'],m['valid_samples']])
        content=out.getvalue();media='text/csv'
    elif format=='json':content=json.dumps(result,indent=2,ensure_ascii=False);media='application/json'
    else:raise HTTPException(400,'Choose json or csv')
    return Response(content,media_type=media,headers={'Content-Disposition':f'attachment; filename=neela-yaan-bulletin-{report_id}.{format}'})

@app.get('/api/latest')
def get_latest(): return latest
@app.get('/api/history')
def history(limit:int=Query(600,ge=1,le=10000),since:str|None=None): return storage.history(limit,since)
@app.get('/api/events')
def events(): return storage.events()
@app.get('/api/export')
def export(limit:int=Query(10000,ge=1,le=100000),since:str|None=None,parameter:str='ocean.temperature'):
    group,_,key=parameter.partition('.')
    if group not in ('ocean','atmosphere','navigation','imu','waves','power'): raise HTTPException(400,'Invalid parameter')
    rows=storage.history(limit,since);out=io.StringIO();w=csv.writer(out);w.writerow(['timestamp','source',parameter,'quality','mission_state'])
    for r in rows: w.writerow([r['timestamp'],r['source'],r.get(group,{}).get(key),r['quality'].get(parameter,''),r['mission']['state']])
    return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename=neela-yaan-telemetry.csv'})
@app.post('/api/telemetry')
async def telemetry(data:Telemetry,x_ingest_token:str=Header('')):
    token=os.getenv('INGEST_TOKEN','')
    if not token or not secrets.compare_digest(token,x_ingest_token): raise HTTPException(401,'Configure and supply X-Ingest-Token')
    try: return await ingest(data.model_dump(mode='json'),'WOKWI')
    except ValueError as e: raise HTTPException(409,str(e))
@app.post('/api/control/{action}')
async def control(action:str):
    global running,source,mission,processor,pending_external,external_last_timestamp
    if action in ('DEMO','WOKWI'):
        source=action;processor=Processor();mission=MissionManager();pending_external=None;external_last_timestamp=None
    elif action=='start': running=True;mission=MissionManager();storage.event('STM32 INITIALIZES','Software controller emulation' if source=='DEMO' else 'Awaiting external firmware telemetry');storage.event('SENSORS INITIALIZE',source)
    elif action=='pause': running=False
    elif action=='reset': faults.clear();mission=MissionManager();processor=Processor();running=True
    elif action.startswith(('fail_','restore_')):
        if source!='DEMO': raise HTTPException(409,'Fault injection is only available in DEMO mode')
        verb,key=action.split('_',1)
        if key not in ('gps','satellite','battery','sensor','ice'): raise HTTPException(400,'Unknown fault')
        faults[key]=verb=='fail'
    else: raise HTTPException(400,'Unknown control')
    storage.event('OPERATOR COMMAND',action)
    return health()
@app.websocket('/ws')
async def socket(sock:WebSocket):
    await sock.accept();ws.clients.add(sock)
    if latest: await sock.send_json({'type':'telemetry','data':latest,'events':storage.events()[:30]})
    try:
        while True:
            await sock.receive_text();await sock.send_json({'type':'heartbeat','health':health()})
    except Exception: pass
    finally: ws.clients.discard(sock)
for section in ('ocean','atmosphere','navigation','waves','power','mission','ice'):
    def make_endpoint(s):
        def endpoint(): return latest.get(s) if latest else None
        return endpoint
    app.add_api_route('/api/'+section,make_endpoint(section),methods=['GET'])
