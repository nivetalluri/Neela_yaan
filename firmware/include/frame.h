#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
struct Frame { JsonDocument json; bool valid=true; float ice=0; const char* state="INITIALIZATION"; };
