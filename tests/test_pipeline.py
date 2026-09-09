import unittest,os,tempfile
from backend.simulator import sample
from backend.telemetry_models import Telemetry
from backend.data_processor import Processor
from backend.ice_algorithm import evaluate
from backend.mission_manager import MissionManager
from backend.storage import Storage
from backend.communication_manager import CommunicationManager
class PipelineTests(unittest.TestCase):
 def process(self,f=None):return Processor().process(Telemetry.model_validate(sample(8,f or {})).model_dump(mode='json'))
 def state(self,d):
  m=MissionManager();m.cycles=2
  return m.evaluate(d,evaluate(d))[0]['state']
 def test_normal(self):self.assertEqual(self.state(self.process()),'NORMAL_OPERATION')
 def test_battery(self):self.assertEqual(self.state(self.process({'battery':True})),'LOW_POWER')
 def test_gps(self):
  d=self.process({'gps':True});self.assertIsNone(d['navigation']['latitude']);self.assertEqual(self.state(d),'GPS_LOSS');self.assertEqual(evaluate(d)['level'],'UNKNOWN')
 def test_satellite(self):self.assertEqual(self.state(self.process({'satellite':True})),'COMMUNICATION_LOSS')
 def test_ice(self):
  d=self.process({'ice':True});self.assertEqual(evaluate(d)['level'],'HIGH');self.assertEqual(self.state(d),'ICE_WARNING')
 def test_invalid(self):
  d=sample(0,{});d['ocean']['temperature']=999;d=Processor().process(Telemetry.model_validate(d).model_dump(mode='json'))
  self.assertIsNone(d['ocean']['temperature']);self.assertEqual(d['quality']['ocean.temperature'],'INVALID');self.assertEqual(self.state(d),'SENSOR_FAULT')
 def test_missing(self):
  d=sample(0,{});del d['ocean']['ph'];d=Processor().process(Telemetry.model_validate(d).model_dump(mode='json'));self.assertEqual(d['quality']['ocean.ph'],'MISSING')
 def test_nonfinite_rejected(self):
  d=sample(0,{});d['ocean']['temperature']=float('nan')
  with self.assertRaises(ValueError):Telemetry.model_validate(d)
 def test_persistence_buffer(self):
  with tempfile.TemporaryDirectory() as tmp:
   old=os.environ.get('DATABASE_PATH');os.environ['DATABASE_PATH']=tmp+'/test.sqlite3'
   s=Storage();c=CommunicationManager(s);s.save(self.process());s.save(self.process())
   self.assertEqual(c.transmit(False)['pending'],2)
   s2=Storage();self.assertEqual(len(s2.history()),2);self.assertEqual(s2.counts()['pending'],2)
   self.assertEqual(c.transmit(True)['pending'],0);self.assertEqual(s.counts()['transmitted'],2)
   s.db.close();s2.db.close()
   if old:os.environ['DATABASE_PATH']=old
   else:os.environ.pop('DATABASE_PATH',None)
 def test_emergency_and_safe(self):
  d=self.process();d['power']['battery_percentage']=2;self.assertEqual(self.state(d),'EMERGENCY')
  d=self.process();d['quality']={str(i):'MISSING' for i in range(20)};self.assertEqual(self.state(d),'SAFE_MODE')
 def test_critical(self):
  d=self.process({'ice':True});d['ocean']['salinity']=31;d['ocean']['depth']=2;d['waves']['height']=.2
  self.assertEqual(self.state(d),'ICE_AVOIDANCE')
if __name__=='__main__':unittest.main()
