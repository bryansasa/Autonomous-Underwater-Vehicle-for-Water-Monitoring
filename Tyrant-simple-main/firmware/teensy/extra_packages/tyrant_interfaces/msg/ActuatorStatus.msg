# Software/actuator-boundary health. Physical PWM output remains disabled
# unless an explicit physical-output build flag is used with valid pins.

uint64 timestamp_us
uint8 backend_type
uint8 fault_code

bool configured
bool ready
bool physical_output_enabled
bool fault_latched

uint32 apply_count
uint32 reject_count
uint32 neutralize_count
uint32 command_age_us

uint16[8] pulse_us
