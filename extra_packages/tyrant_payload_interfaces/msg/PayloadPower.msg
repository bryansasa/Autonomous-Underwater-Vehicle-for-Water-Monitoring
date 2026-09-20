uint8 NOT_INITIALIZED=0
uint8 INITIALIZING=1
uint8 READY=2
uint8 STALE=3
uint8 ERROR=4

uint8 PAYLOAD_SENSOR_RAIL=1
uint8 THRUSTER_BUS=2

uint32 sequence
uint64 timestamp_us
uint8 monitor_id
float32 bus_voltage_v
float32 current_a
float32 power_w
bool valid
uint8 sensor_state
uint32 error_count
