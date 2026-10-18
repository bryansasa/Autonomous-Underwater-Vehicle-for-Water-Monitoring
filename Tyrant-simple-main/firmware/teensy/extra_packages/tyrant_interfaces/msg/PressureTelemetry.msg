uint8 NOT_INITIALIZED=0
uint8 INITIALIZING=1
uint8 READY=2
uint8 STALE=3
uint8 ERROR=4

uint8 sensor_state
uint32 sequence
uint64 timestamp_us
float32 pressure_pa
float32 temperature_c
bool valid

uint32 read_attempts
uint32 read_successes
uint32 samples_produced
uint32 error_count
