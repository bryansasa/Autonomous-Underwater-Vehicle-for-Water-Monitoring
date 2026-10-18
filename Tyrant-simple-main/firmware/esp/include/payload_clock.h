#pragma once
#include <stdint.h>
#ifdef PAYLOAD_NATIVE_TEST
uint64_t payloadTimeUs();
#else
#include <esp_timer.h>
inline uint64_t payloadTimeUs() { return static_cast<uint64_t>(esp_timer_get_time()); }
#endif
