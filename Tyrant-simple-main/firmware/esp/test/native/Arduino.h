#pragma once
#include <stdint.h>
#include <stddef.h>
#include <math.h>
#include <map>
#include <vector>
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define ADC_11db 3
extern uint64_t test_time_us;
extern std::map<int,int> test_levels, test_modes;
inline unsigned long millis() { return static_cast<uint32_t>(test_time_us/1000); }
inline void pinMode(int pin, int mode) { test_modes[pin]=mode; }
inline void digitalWrite(int pin, int level) { test_levels[pin]=level; }
inline void analogReadResolution(int) {}
inline void analogSetPinAttenuation(int,int) {}
inline uint32_t analogReadMilliVolts(int) { return 1283; }
