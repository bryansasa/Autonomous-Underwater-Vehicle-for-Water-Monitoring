# Synchronized SysID sample for grey-box model identification.
# BODY frame is FRD. Depth and body Z are positive down.

uint64 timestamp_us
uint32 experiment_id
uint16 profile_id
uint32 sample_sequence

uint8 mode
bool propulsion_allowed
bool command_fresh

# Operator/reference-side input.
uint32 manual_sequence
float32 manual_surge
float32 manual_sway
float32 manual_heave
float32 manual_roll
float32 manual_pitch
float32 manual_yaw

# Controller output / vehicle wrench request.
uint32 wrench_source_sequence
float32 wrench_x
float32 wrench_y
float32 wrench_z
float32 wrench_k
float32 wrench_m
float32 wrench_n
bool wrench_enabled

# Actuator-side input accepted by the current backend.
# Normalized commands, not measured thrust or PWM pulse widths.
# Mock/HIL data validates software only; characterized PWM hardware is needed
# before these commands can serve as real-vehicle SysID input records.
bool thruster_command_valid
float32[8] thruster_command

# Reduced measured/estimated output.
uint8 estimator_status
float32 roll
float32 pitch
float32 yaw
float32 angular_velocity_x
float32 angular_velocity_y
float32 angular_velocity_z
float32 yaw_rate_bias
float32 depth
bool attitude_valid
bool heading_valid
bool depth_valid

# Raw sensor channels retained for offline identification/validation.
bool imu_valid
float32 accel_x
float32 accel_y
float32 accel_z
float32 gyro_x
float32 gyro_y
float32 gyro_z

bool pressure_valid
float32 pressure_pa
float32 temperature_c
