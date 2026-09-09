#pragma once
#include "frame.h"
namespace power_manager {
// Fixed acquisition contract: record every 7 seconds, independent of mission state.
// Physical load shedding / STOP-STANDBY remain hardware integration work.
inline unsigned long interval(Frame &f){(void)f;return 7000;}
}
