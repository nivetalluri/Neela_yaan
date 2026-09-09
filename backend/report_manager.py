"""Persistent 10-day ocean-condition digests delivered to the local dashboard inbox."""
import json, math, sqlite3
from datetime import datetime, timezone, timedelta
from .mission_manager import now

REPORT_SECONDS=10*24*60*60
METRICS={
 'ocean.temperature':('Water temperature','°C'), 'ocean.salinity':('Salinity','PSU'),
 'ocean.conductivity':('Conductivity','mS/cm'), 'ocean.depth':('Depth','m'),
 'ocean.pressure':('Water pressure','dbar'), 'ocean.dissolved_oxygen':('Dissolved oxygen','mg/L'),
 'ocean.ph':('pH','pH'), 'ocean.current':('Modeled current','m/s'),
 'atmosphere.air_temperature':('Air temperature','°C'), 'atmosphere.pressure':('Air pressure','hPa'),
 'atmosphere.humidity':('Humidity','%'), 'atmosphere.wind_speed':('Wind speed','m/s'),
 'waves.height':('Significant wave height','m'), 'waves.period':('Dominant period','s'),
 'power.battery_percentage':('Battery charge','%')}

def utc(s):return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)
class ReportManager:
 def __init__(self,storage):
  self.storage=storage;self.db=storage.db
  self.db.executescript('''
  CREATE INDEX IF NOT EXISTS samples_timestamp_idx ON samples(timestamp);
  CREATE TABLE IF NOT EXISTS report_schedule(id INTEGER PRIMARY KEY CHECK(id=1),anchor TEXT NOT NULL,next_due TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY,kind TEXT NOT NULL,period_start TEXT NOT NULL,period_end TEXT NOT NULL,generated_at TEXT NOT NULL,unread INTEGER NOT NULL DEFAULT 1,payload TEXT NOT NULL,UNIQUE(kind,period_start,period_end));
  ''')
  anchor=now();due=(utc(anchor)+timedelta(seconds=REPORT_SECONDS)).isoformat()
  self.db.execute('INSERT OR IGNORE INTO report_schedule(id,anchor,next_due) VALUES(1,?,?)',(anchor,due));self.db.commit()
 def status(self):
  a,n=self.db.execute('SELECT anchor,next_due FROM report_schedule WHERE id=1').fetchone()
  total,unread=self.db.execute('SELECT count(*),coalesce(sum(unread),0) FROM reports').fetchone()
  return {'interval_days':10,'interval_seconds':REPORT_SECONDS,'anchor':a,'next_due':n,'destination':'DASHBOARD INBOX','total':total,'unread':unread,'server_utc':now(),'scheduler':'ACTIVE WHILE BACKEND RUNS; CATCH-UP ON RESTART'}
 def build(self,start,end,kind):
  # One aggregate pass. Do not load 123,000 complete telemetry frames into memory.
  expressions=['count(*)']
  for path in METRICS:
   expr=f"json_extract(payload, '$.{path}')"
   expressions += [f'min({expr})',f'max({expr})',f'avg({expr})',f'count({expr})']
  row=self.db.execute('SELECT '+','.join(expressions)+' FROM samples WHERE timestamp>=? AND timestamp<?',(start,end)).fetchone()
  count=row[0];last=self.db.execute('SELECT payload FROM samples WHERE timestamp>=? AND timestamp<? ORDER BY timestamp DESC LIMIT 1',(start,end)).fetchone()
  latest=json.loads(last[0]) if last else None
  metrics={}
  for i,(path,(label,unit)) in enumerate(METRICS.items()):
   lo,hi,mean,n=row[1+i*4:5+i*4];g,k=path.split('.')
   metrics[path]={'label':label,'unit':unit,'min':lo,'max':hi,'mean':mean,'valid_samples':n,'latest':latest.get(g,{}).get(k) if latest else None}
  def counts(path):
   return {str(k):n for k,n in self.db.execute(f"SELECT coalesce(json_extract(payload,'$.{path}'),'UNKNOWN'),count(*) FROM samples WHERE timestamp>=? AND timestamp<? GROUP BY 1",(start,end))}
  sources=counts('source');states=counts('mission.state');risks=counts('ice.level')
  bad=self.db.execute("SELECT count(*) FROM samples s WHERE timestamp>=? AND timestamp<? AND EXISTS(SELECT 1 FROM json_each(s.payload,'$.quality') WHERE value IN ('INVALID','MISSING'))",(start,end)).fetchone()[0]
  coverage_days=max(0,(utc(end)-utc(start)).total_seconds()/86400)
  expected=round(coverage_days*86400/7)
  summary=[]
  for path in ['ocean.temperature','ocean.salinity','ocean.dissolved_oxygen','waves.height']:
   m=metrics[path]
   if m['mean'] is not None:summary.append(f"{m['label']} averaged {m['mean']:.2f} {m['unit']} (range {m['min']:.2f}–{m['max']:.2f}).")
  if risks.get('HIGH',0)+risks.get('CRITICAL',0):summary.append(f"Elevated prototype ice risk appeared in {risks.get('HIGH',0)+risks.get('CRITICAL',0)} samples; this is not a validated ice forecast.")
  if not count:summary=['No observations were recorded in this reporting window. No ocean conditions can be inferred.']
  return {'title':'Ocean conditions bulletin','kind':kind,'period_start':start,'period_end':end,'generated_at':now(),'delivery':'DELIVERED TO DASHBOARD INBOX','sample_count':count,'expected_samples_at_7s':expected,'coverage_percent':min(100,round(100*count/expected,1)) if expected else 0,'window_days':round(coverage_days,3),'samples_with_unavailable_channels':bad,'sources':sources,'states':states,'ice_risk_counts':risks,'metrics':metrics,'latest_position':latest.get('navigation') if latest else None,'latest_sample_at':latest.get('timestamp') if latest else None,'summary':summary,'disclaimer':'Observed records only. DEMO / WOKWI sensor-model data are not real ocean measurements. Quality bounds are prototype checks; no scientific forecast or operational safety certification. Expected count assumes seven-second sampling throughout the window; older records may use a different cadence.'}
 def save(self,payload):
  cur=self.db.execute('INSERT OR IGNORE INTO reports(kind,period_start,period_end,generated_at,payload) VALUES(?,?,?,?,?)',(payload['kind'],payload['period_start'],payload['period_end'],payload['generated_at'],json.dumps(payload)))
  return cur.lastrowid if cur.rowcount else None
 def run_due(self,at=None):
  at=utc(at or now());completed=[]
  for _ in range(32):
   due=utc(self.status()['next_due'])
   if due>at:break
   start=due-timedelta(seconds=REPORT_SECONDS)
   report=self.build(start.isoformat(),due.isoformat(),'SCHEDULED')
   # Report and next due advance together, making restart catch-up idempotent.
   with self.db:
    id=self.save(report)
    self.db.execute('UPDATE report_schedule SET next_due=? WHERE id=1',((due+timedelta(seconds=REPORT_SECONDS)).isoformat(),))
   if id:
    self.storage.event('OCEAN REPORT DELIVERED',f'10-day bulletin #{id} delivered to dashboard inbox')
    completed.append(id)
  return completed
 def preview(self):
  end=utc(now());anchor=utc(self.status()['anchor']);start=max(anchor,end-timedelta(seconds=REPORT_SECONDS))
  p=self.build(start.isoformat(),end.isoformat(),'PREVIEW')
  id=self.save(p);self.db.commit();self.storage.event('REPORT PREVIEW CREATED',f'Partial-window bulletin #{id}; regular 10-day schedule unchanged')
  return self.get(id)
 def list(self):
  rows=self.db.execute('SELECT id,kind,period_start,period_end,generated_at,unread,json_extract(payload,\'$.sample_count\'),json_extract(payload,\'$.sources\') FROM reports ORDER BY id DESC LIMIT 100')
  return [dict(id=r[0],kind=r[1],period_start=r[2],period_end=r[3],generated_at=r[4],unread=bool(r[5]),sample_count=r[6],sources=json.loads(r[7])) for r in rows]
 def get(self,id):
  r=self.db.execute('SELECT payload,unread FROM reports WHERE id=?',(id,)).fetchone()
  return {**json.loads(r[0]),'id':id,'unread':bool(r[1])} if r else None
 def read(self,id):
  self.db.execute('UPDATE reports SET unread=0 WHERE id=?',(id,));self.db.commit()
