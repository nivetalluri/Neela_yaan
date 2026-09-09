#pragma once
#include "frame.h"
namespace ice_detection {
inline void evaluate(Frame &f){float water=f.json["ocean"]["temperature"],air=f.json["atmosphere"]["air_temperature"];
f.ice=(water<-.8f?35:water<1?20:5)+(air<-10?25:air<-2?15:0)+(f.json["ocean"]["salinity"].as<float>()<33?10:5)+(abs(f.json["navigation"]["latitude"].as<float>())>60?15:5)+(f.json["waves"]["height"].as<float>()<1?10:0)+(f.json["ocean"]["depth"].as<float>()<10?5:0);}
}
