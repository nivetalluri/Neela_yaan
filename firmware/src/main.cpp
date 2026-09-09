#include "data_acquisition.h"
#include "data_validation.h"
#include "data_processing.h"
#include "navigation_manager.h"
#include "ice_detection.h"
#include "mission_manager.h"
#include "storage_manager.h"
#include "communication_manager.h"
#include "power_manager.h"
Frame frame;
unsigned long previous=0,period=7000;
void setup(){communication_manager::initialize();sensor_manager::initialize();}
void loop(){
 if(millis()-previous<period)return;previous+=period;
 data_acquisition::acquire(frame);data_validation::validate(frame);
 data_processing::process(frame);navigation_manager::update(frame);
 ice_detection::evaluate(frame);mission_manager::update(frame);
 storage_manager::store(frame);communication_manager::transmit(frame);
 period=power_manager::interval(frame);
}
