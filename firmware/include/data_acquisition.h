#pragma once
#include "sensor_manager.h"
namespace data_acquisition { inline void acquire(Frame &f){f.json.clear();sensor_manager::read(f);} }
