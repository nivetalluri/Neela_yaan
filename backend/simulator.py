import math, random
from .mission_manager import now

def sample(t,f):
    noise=lambda s: random.gauss(0,s)
    ice=f.get('ice',False)
    # Great-circle forward geodesic in WGS84-style geographic coordinates.
    # This is a SIMULATED position, not real GNSS or browser geolocation.
    lat0,lon0,bearing=map(math.radians,(-64.821,72.431,114.0))
    angular_distance=.74*t/6371008.8
    lat=math.asin(math.sin(lat0)*math.cos(angular_distance)+math.cos(lat0)*math.sin(angular_distance)*math.cos(bearing))
    lon=lon0+math.atan2(math.sin(bearing)*math.sin(angular_distance)*math.cos(lat0),math.cos(angular_distance)-math.sin(lat0)*math.sin(lat))
    latitude=math.degrees(lat);longitude=(math.degrees(lon)+180)%360-180
    return {'timestamp':now(),
    'ocean':{'temperature':(-1.4 if ice else 2.8)+noise(.07),'conductivity':32.7+noise(.1),'salinity':34.2+noise(.04),'pressure':12.6+noise(.2),'depth':12.8+noise(.2),'dissolved_oxygen':8.9+noise(.06),'ph':8.1+noise(.015),'current':.34+noise(.02)},
    'atmosphere':{'air_temperature':(-14 if ice else -4.2)+noise(.15),'pressure':1008+noise(.3),'humidity':71+noise(.4),'wind_speed':12.4+noise(.4),'wind_direction':220+noise(2)},
    'navigation':{'latitude':latitude,'longitude':longitude,'speed':.74,'heading':114.0,'gps_fix':not f.get('gps'),'satellites':0 if f.get('gps') else 9,'accuracy':2.4,'gps_status':'LOST' if f.get('gps') else 'ACTIVE'},
    'imu':{'acc_x':.12*math.sin(t),'acc_y':.05*math.cos(t),'acc_z':9.80665+.4*math.sin(2*math.pi*t/8.2)+noise(.03),'gyro_x':.01,'gyro_y':.02,'gyro_z':.04,'pitch':1.8*math.sin(t/4),'roll':.6*math.cos(t/3)},
    'waves':{'height':2.4+noise(.06),'period':8.2+noise(.05),'frequency':1/8.2},
    'power':{'battery_percentage':14 if f.get('battery') else max(25,82-t/20000),'battery_voltage':11.2 if f.get('battery') else 12.4,'solar_power':18.4+noise(.3),'load_power':7.8+noise(.1)},
    'communication':{'gps_status':'LOST' if f.get('gps') else 'FIX','satellite_status':'OFFLINE' if f.get('satellite') else 'CONNECTED'}}
