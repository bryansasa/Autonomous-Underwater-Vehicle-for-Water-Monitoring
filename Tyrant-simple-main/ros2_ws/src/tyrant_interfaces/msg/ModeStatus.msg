uint8 BOOT=0
uint8 IDLE=1
uint8 MANUAL=2
uint8 AUTO=3
uint8 SAFE=4
uint8 FAULT=5
uint8 EMERGENCY=6

uint8 REASON_NONE=0
uint8 REASON_REQUEST_ACCEPTED=1
uint8 REASON_INVALID_MODE=2
uint8 REASON_TRANSITION_NOT_ALLOWED=3
uint8 REASON_SYSTEM_UNHEALTHY=4
uint8 REASON_AUTONOMY_NOT_READY=5
uint8 REASON_COMMUNICATION_TIMEOUT=6
uint8 REASON_FAULT_LATCHED=7
uint8 REASON_EMERGENCY_LATCHED=8

uint32 request_id
uint8 current_mode
uint8 requested_mode
bool request_accepted
uint8 reason
bool communication_healthy
bool propulsion_allowed
