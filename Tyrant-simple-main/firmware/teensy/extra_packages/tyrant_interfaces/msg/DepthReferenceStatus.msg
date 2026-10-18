uint8 NONE=0
uint8 REQUEST_ACCEPTED=1
uint8 INVALID_COMMAND=2
uint8 VEHICLE_NOT_IDLE=3
uint8 PRESSURE_NOT_READY=4
uint8 PRESSURE_INVALID=5
uint8 SET_REFERENCE_FAILED=6

uint32 request_id
uint8 command
bool accepted
uint8 reason
bool reference_valid
float32 surface_pressure_pa
