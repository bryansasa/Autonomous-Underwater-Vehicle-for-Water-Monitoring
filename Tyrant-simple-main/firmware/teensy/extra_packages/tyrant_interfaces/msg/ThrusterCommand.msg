# Normalized 8-channel actuator command produced by the allocator.
# BODY frame convention remains FRD. This message is currently driven by
# the selected actuator backend. Physical PWM remains disabled by default.

uint64 timestamp_us
uint32 source_sequence

uint8 allocation_status
bool allocator_ready
bool valid
bool enabled
bool saturated
bool mock_backend

float32 residual_norm
float32[8] command
