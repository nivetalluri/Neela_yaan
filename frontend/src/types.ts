// Sensor interfaces generated from backend Pydantic schema.
export interface Atmosphere {
  air_temperature: number | null;
  pressure: number | null;
  humidity: number | null;
  wind_speed: number | null;
  wind_direction: number | null;
}
export interface Communication {
  gps_status: string;
  satellite_status: 'CONNECTED' | 'OFFLINE';
}
export interface Imu {
  acc_x: number | null;
  acc_y: number | null;
  acc_z: number | null;
  gyro_x: number | null;
  gyro_y: number | null;
  gyro_z: number | null;
  pitch: number | null;
  roll: number | null;
}
export interface MissionInput {
  state: string;
  ice_risk: string;
}
export interface Navigation {
  latitude: number | null;
  longitude: number | null;
  speed: number | null;
  heading: number | null;
  gps_fix: boolean;
  satellites: number | null;
  accuracy: number | null;
  gps_status: 'ACTIVE' | 'SLEEP' | 'RECOVERING' | 'LOST';
}
export interface Ocean {
  temperature: number | null;
  conductivity: number | null;
  salinity: number | null;
  pressure: number | null;
  depth: number | null;
  dissolved_oxygen: number | null;
  ph: number | null;
  current: number | null;
}
export interface Power {
  battery_percentage: number | null;
  battery_voltage: number | null;
  solar_power: number | null;
  load_power: number | null;
}
export interface Waves {
  height: number | null;
  period: number | null;
  frequency: number | null;
}
export interface Telemetry {
 id: number; timestamp: string; received_at: string; source: 'DEMO'|'WOKWI';
 ocean: Ocean; atmosphere: Atmosphere; navigation: Navigation; imu: Imu; waves: Waves; power: Power;
 communication: Communication & {packet_count:number;transmitted:number;pending:number;last_transmission:string|null;transport:string};
 mission: {state:string;reason:string;previous:string;next_action:string;since:string;ice_risk:string;operating_mode:string};
 ice: {score:number|null;level:string;status:string;inputs:Record<string,number|null>;recommendation:string};
 quality:Record<string,'GOOD'|'WARNING'|'INVALID'|'MISSING'>;
 motion:{rms:number|null;spectrum:{frequency:number;power:number}[];method:string};
 pipeline:{name:string;timestamp:string;status:string;errors:number}[];
}
export interface MissionEvent {id:number;timestamp:string;type:string;detail:string}
export interface Health {source:string;running:boolean;faults:Record<string,boolean>;mqtt_configured:boolean;mqtt_connected:boolean;last_packet_age:number|null}
