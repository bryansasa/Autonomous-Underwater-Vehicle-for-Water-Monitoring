uint8 POLICY_NONE=0
uint8 POLICY_ZERO_THRUST=1
uint8 POLICY_CONTROLLED_SURFACE=2

uint8 STATE_INACTIVE=0
uint8 STATE_ACTIVE=1
uint8 STATE_COMPLETE=2
uint8 STATE_FAILED=3

uint8 REASON_NONE=0
uint8 REASON_ACCEPTED=1
uint8 REASON_INVALID_STATE=2
uint8 REASON_TIMEOUT=3
uint8 REASON_SURFACE_REACHED=4

uint32 request_id
uint8 command
bool accepted
uint8 policy
uint8 state
uint8 reason
uint32 elapsed_ms
bool actuation_requested
