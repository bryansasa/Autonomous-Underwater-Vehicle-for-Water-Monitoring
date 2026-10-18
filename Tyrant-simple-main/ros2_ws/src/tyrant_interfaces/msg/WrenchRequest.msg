# Normalized body-FRD wrench request.
# x/y/z/k/m/n are dimensionless in [-1.0, +1.0].
# Feeds the TAM/allocator and selected actuator backend; not a physical N/Nm wrench.
# Production output remains disabled; mock/HIL profiles use virtual thrusters.

uint32 source_sequence

float32 x
float32 y
float32 z

float32 k
float32 m
float32 n

bool command_fresh
bool enabled
