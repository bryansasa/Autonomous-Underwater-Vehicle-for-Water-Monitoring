uint8 NONE=0
uint8 REQUEST_ACCEPTED=1
uint8 INVALID_SENSOR=2
uint8 POWER_TRANSITION_FAILED=3
uint8 SENSOR_BUSY=4
uint8 SYSTEM_NOT_READY=5

uint32 request_id
uint8 sensor_id
bool requested_enable
bool accepted
uint8 reason
bool actual_enabled
