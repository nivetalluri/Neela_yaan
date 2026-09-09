import math
import numpy as np
from collections import deque
RANGES = {
'ocean': {'temperature':(-3,40),'conductivity':(0,70),'salinity':(0,45),'pressure':(0,12000),'depth':(0,11000),'dissolved_oxygen':(0,20),'ph':(0,14),'current':(0,10)},
'atmosphere': {'air_temperature':(-90,60),'pressure':(800,1100),'humidity':(0,100),'wind_speed':(0,100),'wind_direction':(0,360)},
'navigation': {'latitude':(-90,90),'longitude':(-180,180),'speed':(0,30),'heading':(0,360),'satellites':(0,100),'accuracy':(0,10000)},
'imu': {**{k:(-100,100) for k in ['acc_x','acc_y','acc_z','gyro_x','gyro_y','gyro_z']},'pitch':(-180,180),'roll':(-180,180)},
'waves': {'height':(0,40),'period':(0.5,100),'frequency':(0.01,2)},
'power': {'battery_percentage':(0,100),'battery_voltage':(0,60),'solar_power':(0,500),'load_power':(0,500)}}
class Processor:
    def __init__(self):
        self.previous = {}; self.motion = deque(maxlen=128)
    def process(self, data):
        quality = {}; raw = {g:dict(data[g]) for g in RANGES}
        for group, fields in RANGES.items():
            for key, (lo,hi) in fields.items():
                path=f'{group}.{key}'; v=data[group].get(key)
                q='GOOD'
                if v is None: q='MISSING'
                elif not math.isfinite(v) or not lo <= v <= hi: q='INVALID'; v=None
                elif group in ('ocean','atmosphere'):
                    prev=self.previous.get(path, v)
                    if abs(v-prev) > (hi-lo)*.08: q='WARNING'
                    # Low-pass physical measurements, never substitute missing/invalid values.
                    v=round(.65*v+.35*prev,4)
                    self.previous[path]=v
                data[group][key]=v; quality[path]=q
        nav=data['navigation']
        if not nav['gps_fix']:
            nav['gps_status']='LOST'
            for k in ('latitude','longitude','accuracy'):
                nav[k]=None; quality['navigation.'+k]='MISSING'
        z=data['imu']['acc_z']
        if z is not None: self.motion.append((data['timestamp'],z-9.80665))
        rms=None; spectrum=[]
        if len(self.motion)>=8:
            from datetime import datetime
            ts=[datetime.fromisoformat(x[0]).timestamp() for x in self.motion]
            dt=(ts[-1]-ts[0])/(len(ts)-1)
            if dt>0:
                x=np.array([x[1] for x in self.motion]); x=x-x.mean()
                rms=float(np.sqrt(np.mean(x*x)))
                power=np.abs(np.fft.rfft(x*np.hanning(len(x))))**2/len(x)
                spectrum=[{'frequency':round(float(f),4),'power':round(float(p),5)} for f,p in zip(np.fft.rfftfreq(len(x),dt),power)]
        data.update(quality=quality,raw=raw,motion={'rms':rms,'spectrum':spectrum,'method':'Detrended vertical acceleration; Hann window FFT. Low-rate prototype, not validated wave reconstruction.'})
        return data
