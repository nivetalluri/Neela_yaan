#pragma once
#include "frame.h"
namespace navigation_manager {
inline void update(Frame &f){auto n=f.json["navigation"].to<JsonObject>();
float t=millis()/1000.0f;n["latitude"]=-64.821f+.006f*sin(t/1000);n["longitude"]=72.431f+t*.000006f;
n["speed"]=.74f;n["heading"]=114;n["gps_fix"]=true;n["satellites"]=9;n["accuracy"]=2.4f;n["gps_status"]="ACTIVE";}
}
