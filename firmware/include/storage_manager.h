#pragma once
#include "frame.h"
namespace storage_manager {
// Two-slot VOLATILE journal for integration bring-up. Not power-loss safe.
// Replace with SD/FRAM journaling plus modem ACK handling on deployed hardware.
static char slots[2][2048];
static size_t lengths[2]={0,0};
static uint8_t next=0;
inline void store(Frame &f){lengths[next]=serializeJson(f.json,slots[next],sizeof(slots[next]));next=(next+1)%2;}
}
