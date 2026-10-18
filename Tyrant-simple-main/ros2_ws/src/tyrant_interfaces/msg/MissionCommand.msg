uint8 COMMAND_CLEAR=0
uint8 COMMAND_APPEND=1
uint8 COMMAND_START=2
uint8 COMMAND_STOP=3
uint8 COMMAND_STATUS=255

uint8 STEP_WAIT=1
uint8 STEP_SURGE_TIME=2
uint8 STEP_SWAY_TIME=3
uint8 STEP_DIVE_TO_DEPTH=4
uint8 STEP_TURN_TO_HEADING=5
uint8 STEP_SURFACE_TO_DEPTH=6

uint32 request_id
uint8 command
uint8 step_type
float32 target
float32 effort
uint32 duration_ms
float32 tolerance
