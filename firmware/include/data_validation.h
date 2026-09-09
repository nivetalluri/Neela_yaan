#pragma once
#include "frame.h"
namespace data_validation {
inline void validate(Frame &f){float temp=f.json["ocean"]["temperature"];f.valid=isfinite(temp)&&temp>=-3&&temp<=40;}
}
