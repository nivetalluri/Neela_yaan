#pragma once
#include "frame.h"
namespace mission_manager {
inline void update(Frame &f){float b=f.json["power"]["battery_percentage"];static unsigned long cycles=0;cycles++;
f.state=cycles==1?"INITIALIZATION":cycles==2?"DEPLOYED":b<5?"EMERGENCY":!f.valid?"SENSOR_FAULT":f.ice>80?"ICE_AVOIDANCE":f.ice>60?"ICE_WARNING":b<20?"LOW_POWER":"NORMAL_OPERATION";
auto m=f.json["mission"].to<JsonObject>();m["state"]=f.state;m["ice_risk"]=f.ice<=30?"LOW":f.ice<=60?"MODERATE":f.ice<=80?"HIGH":"CRITICAL";}
}
