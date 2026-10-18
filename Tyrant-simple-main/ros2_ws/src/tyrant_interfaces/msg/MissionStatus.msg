uint8 STATE_EMPTY=0
uint8 STATE_READY=1
uint8 STATE_ACTIVE=2
uint8 STATE_COMPLETE=3
uint8 STATE_STOPPED=4
uint8 STATE_FAILED=5

uint8 REASON_NONE=0
uint8 REASON_ACCEPTED=1
uint8 REASON_NO_STEPS=2
uint8 REASON_STEP_LIST_FULL=3
uint8 REASON_INVALID_STEP=4
uint8 REASON_STATE_INVALID=5
uint8 REASON_NOT_ACTIVE=6
uint8 REASON_COMPLETE=7

uint32 request_id
uint8 command
bool accepted
uint8 state
uint8 reason
uint8 step_count
uint8 current_step
uint8 current_step_type
bool active
