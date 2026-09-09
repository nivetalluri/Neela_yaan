#pragma once
#include "frame.h"
namespace communication_manager {
inline void initialize(){Serial.begin(115200);}
inline void transmit(Frame &f){auto c=f.json["communication"].to<JsonObject>();c["gps_status"]="FIX";c["satellite_status"]="CONNECTED";serializeJson(f.json,Serial);Serial.println();}
}
