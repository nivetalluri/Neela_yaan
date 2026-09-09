def evaluate(d):
    o,a,n,w=d['ocean'],d['atmosphere'],d['navigation'],d['waves']
    inputs={'water_temperature':o['temperature'],'air_temperature':a['air_temperature'],'salinity':o['salinity'],'depth':o['depth'],'latitude':n['latitude'],'wave_height':w['height']}
    if any(v is None for v in inputs.values()):
        return {'score':None,'level':'UNKNOWN','status':'INSUFFICIENT DATA','inputs':inputs,'recommendation':'Inspect missing sensors; do not interpret risk as low.'}
    score=round(min(100,max(0,(35 if o['temperature']<-.8 else 20 if o['temperature']<1 else 5)+(25 if a['air_temperature']<-10 else 15 if a['air_temperature']<-2 else 0)+(10 if o['salinity']<33 else 5)+(15 if abs(n['latitude'])>60 else 5)+(10 if w['height']<1 else 0)+(5 if o['depth']<10 else 0))))
    level='LOW' if score<=30 else 'MODERATE' if score<=60 else 'HIGH' if score<=80 else 'CRITICAL'
    return {'score':score,'level':level,'status':'PROTOTYPE • NOT VALIDATED','inputs':inputs,'recommendation':{'LOW':'Continue nominal sampling and position monitoring.','MODERATE':'Monitor thermal conditions and position.','HIGH':'Maintain seven-second recording; monitor position and prepare safe operating mode.','CRITICAL':'Request safe-depth operation; inhibit surfacing (simulated actuator intent only).'}[level]}
