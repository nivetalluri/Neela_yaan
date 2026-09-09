#pragma once
#include "frame.h"
namespace sensor_manager {
inline void initialize(){analogReadResolution(12);pinMode(A0,INPUT);pinMode(A1,INPUT);}
inline void read(Frame &f){
 auto &j=f.json;float t=millis()/1000.0f;
 // All environmental channels are software sensor models, NOT real ocean data.
 auto o=j["ocean"].to<JsonObject>();
 o["temperature"]=-2.0f+40.0f*analogRead(A0)/4095.0f;
 o["conductivity"]=32.7f+.1f*sin(t);o["salinity"]=34.2f+.03f*sin(t/3);
 o["pressure"]=12.6f;o["depth"]=12.8f;o["dissolved_oxygen"]=8.9f;
 o["ph"]=8.1f;o["current"]=.34f;
 auto a=j["atmosphere"].to<JsonObject>();
 a["air_temperature"]=-4.2f;a["pressure"]=1008;a["humidity"]=71;
 a["wind_speed"]=12.4f;a["wind_direction"]=220;
 auto imu=j["imu"].to<JsonObject>();
 imu["acc_x"]=.12f*sin(t);imu["acc_y"]=.05f*cos(t);imu["acc_z"]=9.80665f+.4f*sin(2*PI*t/8.2f);
 imu["gyro_x"]=.01f;imu["gyro_y"]=.02f;imu["gyro_z"]=.04f;
 imu["pitch"]=1.8f*sin(t/4);imu["roll"]=.6f*cos(t/3);
 auto w=j["waves"].to<JsonObject>();w["height"]=2.4f;w["period"]=8.2f;w["frequency"]=1.0f/8.2f;
 auto p=j["power"].to<JsonObject>();p["battery_percentage"]=100.0f*analogRead(A1)/4095.0f;
 p["battery_voltage"]=12.4f;p["solar_power"]=18.4f;p["load_power"]=7.8f;
}
}
