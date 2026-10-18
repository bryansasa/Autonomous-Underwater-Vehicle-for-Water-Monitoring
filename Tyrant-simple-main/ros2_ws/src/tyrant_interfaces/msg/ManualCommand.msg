# Normalized manual vehicle command.
# Each axis is dimensionless and expected in [-1.0, +1.0].
# Body convention: FRD (+X forward, +Y right, +Z down).
#
# Stabilized MANUAL semantics:
# - surge/sway: direct normalized vehicle effort
# - heave: depth-reference rate command (positive = deeper)
# - roll/pitch: bounded attitude-angle reference
# - yaw: heading-reference rate command (positive = clockwise/right)

uint32 sequence

float32 surge
float32 sway
float32 heave

float32 roll
float32 pitch
float32 yaw
