#pragma once
#include "frame.h"
namespace data_processing {
// Filter state belongs to the controller; full per-channel validation is in backend.
inline void process(Frame &f){static float prev=0;static bool first=true;float x=f.json["ocean"]["temperature"];
if(f.valid){if(first){prev=x;first=false;}prev=.65f*x+.35f*prev;f.json["ocean"]["temperature"]=prev;}}
}
