uint8 INITIALIZING=0
uint8 RUNNING=1
uint8 DEGRADED=2
uint8 FAULT=3

uint64 timestamp_us
uint8 status

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
