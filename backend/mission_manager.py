from datetime import datetime, timezone

def now(): return datetime.now(timezone.utc).isoformat()
class MissionManager:
    def __init__(self):
        self.state='INITIALIZATION'; self.previous='—'; self.since=now(); self.cycles=0
    def evaluate(self,d,ice):
        b=d['power']['battery_percentage']; q=d['quality']; self.cycles+=1
        if self.cycles==1: state,reason,action='INITIALIZATION','Controller and sensor self-check','Initialize sensor interfaces'
        elif self.cycles==2: state,reason,action='DEPLOYED','Self-check complete','Begin observation cycle'
        elif b is not None and b<5: state,reason,action='EMERGENCY','Battery critically depleted','Disable nonessential loads; request recovery'
        elif sum(v in ('INVALID','MISSING') for v in q.values())>12: state,reason,action='SAFE_MODE','Multiple unavailable sensor channels','Preserve logs; request intervention'
        elif ice['level']=='CRITICAL': state,reason,action='ICE_AVOIDANCE','Critical prototype ice risk','Request safe depth; inhibit surfacing'
        elif ice['level']=='HIGH': state,reason,action='ICE_WARNING','Elevated prototype ice risk','Maintain 7-second recording; monitor ice conditions'
        elif b is not None and b<20: state,reason,action='LOW_POWER','Battery below 20%','Preserve 7-second recording; reduce nonessential loads'
        elif any(q.get('ocean.'+k) in ('INVALID','MISSING') for k in ['temperature','salinity','pressure']): state,reason,action='SENSOR_FAULT','Critical ocean sensor unavailable','Flag samples; continue healthy channels'
        elif not d['navigation']['gps_fix']: state,reason,action='GPS_LOSS','GNSS fix unavailable','Retry acquisition; retain last known track'
        elif d['communication']['satellite_status']=='OFFLINE': state,reason,action='COMMUNICATION_LOSS','Satellite link unavailable','Buffer packets locally; retry link'
        else: state,reason,action='NORMAL_OPERATION','All critical systems nominal','Continue autonomous observations'
        changed=state!=self.state
        if changed: self.previous=self.state; self.state=state; self.since=now()
        return {'state':state,'reason':reason,'previous':self.previous,'next_action':action,'since':self.since,'ice_risk':ice['level'],'operating_mode':'EMERGENCY' if b is not None and b<5 else 'SURVIVAL' if b is not None and b<10 else 'LOW POWER' if b is not None and b<20 else 'NORMAL'},changed
