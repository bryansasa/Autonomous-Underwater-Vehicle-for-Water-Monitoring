uint8 NOT_INITIALIZED=0
uint8 INITIALIZING=1
uint8 READY=2
uint8 STALE=3
uint8 ERROR=4

uint8 sensor_state
uint32 sequence
uint64 timestamp_us

float32 accel_x
float32 accel_y
float32 accel_z
float32 gyro_x
float32 gyro_y
float32 gyro_z

int16 mag_x_lsb
int16 mag_y_lsb
int16 mag_z_lsb
uint32 mag_sequence

bool valid
bool mag_valid
bool mag_updated

uint32 bytes_received
uint32 register_updates
uint32 samples_produced
uint32 samples_dropped
uint32 error_count
