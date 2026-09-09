from pydantic import BaseModel, ConfigDict, Field, AwareDatetime
from typing import Literal

class Sensor(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
class Ocean(Sensor):
    temperature: float | None = None
    conductivity: float | None = None
    salinity: float | None = None
    pressure: float | None = None
    depth: float | None = None
    dissolved_oxygen: float | None = None
    ph: float | None = None
    current: float | None = None
class Atmosphere(Sensor):
    air_temperature: float | None = None
    pressure: float | None = None
    humidity: float | None = None
    wind_speed: float | None = None
    wind_direction: float | None = None
class Navigation(Sensor):
    latitude: float | None = None
    longitude: float | None = None
    speed: float | None = None
    heading: float | None = None
    gps_fix: bool = False
    satellites: int | None = None
    accuracy: float | None = None
    gps_status: Literal['ACTIVE','SLEEP','RECOVERING','LOST'] = 'ACTIVE'
class Imu(Sensor):
    acc_x: float | None = None
    acc_y: float | None = None
    acc_z: float | None = None
    gyro_x: float | None = None
    gyro_y: float | None = None
    gyro_z: float | None = None
    pitch: float | None = None
    roll: float | None = None
class Waves(Sensor):
    height: float | None = None
    period: float | None = None
    frequency: float | None = None
class Power(Sensor):
    battery_percentage: float | None = None
    battery_voltage: float | None = None
    solar_power: float | None = None
    load_power: float | None = None
class Communication(Sensor):
    gps_status: str = 'FIX'
    satellite_status: Literal['CONNECTED','OFFLINE'] = 'CONNECTED'
class MissionInput(Sensor):
    state: str = 'INITIALIZATION'
    ice_risk: str = 'LOW'
class Telemetry(Sensor):
    timestamp: AwareDatetime
    ocean: Ocean = Field(default_factory=Ocean)
    atmosphere: Atmosphere = Field(default_factory=Atmosphere)
    navigation: Navigation = Field(default_factory=Navigation)
    imu: Imu = Field(default_factory=Imu)
    waves: Waves = Field(default_factory=Waves)
    power: Power = Field(default_factory=Power)
    communication: Communication = Field(default_factory=Communication)
    mission: MissionInput = Field(default_factory=MissionInput)
