import unittest,os,tempfile,json
from datetime import datetime,timezone,timedelta
from backend.storage import Storage
from backend.report_manager import ReportManager,REPORT_SECONDS
class ReportTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=os.environ.get('DATABASE_PATH');os.environ['DATABASE_PATH']=self.tmp.name+'/reports.sqlite3'
  self.storage=Storage();self.reports=ReportManager(self.storage)
 def tearDown(self):
  self.storage.db.close();self.tmp.cleanup()
  if self.old:os.environ['DATABASE_PATH']=self.old
  else:os.environ.pop('DATABASE_PATH',None)
 def test_ten_day_schedule_survives_restart(self):
  a=self.reports.status();b=ReportManager(self.storage).status()
  self.assertEqual(a['next_due'],b['next_due']);self.assertEqual((datetime.fromisoformat(a['next_due'])-datetime.fromisoformat(a['anchor'])).total_seconds(),864000)
 def test_due_catchup_idempotent(self):
  start=datetime.now(timezone.utc)-timedelta(days=21);due=start+timedelta(days=10)
  self.storage.db.execute('UPDATE report_schedule SET anchor=?,next_due=?',(start.isoformat(),due.isoformat()));self.storage.db.commit()
  ids=self.reports.run_due();self.assertEqual(len(ids),2);self.assertEqual(self.reports.run_due(),[])
  for id in ids:self.assertEqual(self.reports.get(id)['sample_count'],0)
 def test_aggregates_and_provenance(self):
  start=datetime.now(timezone.utc)-timedelta(days=10);end=start+timedelta(days=10)
  for i,v in enumerate([1.0,3.0,None]):
   self.storage.save({'timestamp':(start+timedelta(seconds=7*i)).isoformat(),'source':'DEMO','ocean':{'temperature':v},'quality':{'ocean.temperature':'MISSING' if v is None else 'GOOD'},'mission':{'state':'NORMAL_OPERATION'},'ice':{'level':'LOW'}})
  p=self.reports.build(start.isoformat(),end.isoformat(),'SCHEDULED')
  m=p['metrics']['ocean.temperature'];self.assertEqual(m['mean'],2);self.assertEqual(m['valid_samples'],2);self.assertEqual(p['sample_count'],3);self.assertEqual(p['sources'],{'DEMO':3});self.assertEqual(p['samples_with_unavailable_channels'],1)
 def test_preview_does_not_shift_delivery(self):
  before=self.reports.status()['next_due'];p=self.reports.preview()
  self.assertEqual(p['kind'],'PREVIEW');self.assertEqual(before,self.reports.status()['next_due']);self.assertEqual(self.reports.status()['unread'],1)
  self.reports.read(p['id']);self.assertEqual(self.reports.status()['unread'],0)
 def test_end_boundary_excluded(self):
  end=datetime.now(timezone.utc);start=end-timedelta(days=10)
  self.storage.save({'timestamp':end.isoformat(),'ocean':{'temperature':999},'source':'DEMO'})
  self.assertEqual(self.reports.build(start.isoformat(),end.isoformat(),'SCHEDULED')['sample_count'],0)
if __name__=='__main__':unittest.main()
