# Tyrant AUV Coordinate Convention

## Internal vehicle convention

Tyrant AUV uses a marine-style internal convention.

### Body frame

- +X: forward
- +Y: starboard / right
- +Z: down

This is an FRD (Forward-Right-Down) body frame.

### Local navigation frame

The estimator and controller use a local NED-like convention:

- +X: forward / local north reference
- +Y: right / local east reference
- +Z: down

Depth is positive downward.

### Rotation

Angular rates use the right-hand rule:

- roll  : rotation about +X
- pitch : rotation about +Y
- yaw   : rotation about +Z

With +Z down, positive yaw follows the marine/NED convention.

## IMU contract

`ImuSample` values used by the estimator must be expressed in the
Tyrant body FRD frame and use SI units:

- acceleration / specific force: m/s^2
- angular rate: rad/s
- timestamp: local Teensy monotonic microseconds

Accelerometer measurements are not inertial linear acceleration.
The reduced estimator uses their gravity direction for roll/pitch correction;
it does not estimate translational acceleration, velocity, or X/Y position.

The current HWT905 bench bring-up uses the validated sensor-to-body mapping `[+X, -Y, -Z]`. This is the current configuration, while final chassis mounting qualification remains pending. The mapping remains configuration-owned so a future physical remount does not change estimator/control conventions.

## Magnetometer contract

The HWT905 magnetometer provides a 3-axis magnetic-field measurement.

Current firmware stores the magnetic samples after the sensor-to-body mounting
transform as:

- `mag_x_lsb`
- `mag_y_lsb`
- `mag_z_lsb`

The values are currently kept in raw LSB units.

The estimator has hard-iron offset and soft-iron matrix hooks, but the current
development configuration uses zero offsets and an identity matrix. Physical
magnetometer calibration, magnetic-field scaling, and magnetic declination
correction have not been applied.

### Magnetometer freshness

`mag_valid` means that a usable magnetometer measurement has been
received and is currently cached.

`mag_updated` means that a NEW magnetometer measurement was received
for the current core IMU sample.

`mag_sequence` increments only when a new magnetometer measurement
is received.

The estimator must not perform repeated magnetometer corrections
using the same `mag_sequence`.

### Heading convention

Tyrant AUV uses the internal NED-like navigation convention:

- +X: local forward / north reference
- +Y: local right / east reference
- +Z: down

Yaw is a right-hand rotation about +Z.

Therefore positive yaw is clockwise when viewed from above.

Yaw = 0 corresponds to the selected local +X heading reference.

### Important

Raw magnetometer X/Y values are NOT directly equal to yaw.

Heading correction requires:

1. verified sensor-to-body axis mapping,
2. magnetometer calibration,
3. roll/pitch compensation,
4. magnetic-reference handling.

The `[+X, -Y, -Z]` mapping is validated for the current bench bring-up. Final
chassis mounting qualification and full hard/soft-iron magnetic calibration
remain separate hardware-characterization tasks. These documents do not claim
validation in the assembled vehicle's magnetic environment.

## Depth contract

`DepthMeasurement.depth_m` is:

- meters
- zero at the configured surface-pressure reference
- positive downward

## ROS boundary

The internal marine FRD/NED convention is separate from ROS standard
frame conventions. Conversion must be performed later when publishing
standard ROS messages that require another frame convention.

## Configurable IMU mounting

The physical HWT905 orientation is not part of the estimator model.

All HWT905 measurements are transformed from the sensor frame into
the Tyrant body FRD frame before leaving the HWT905 driver.

The production mounting configuration is defined by:

`TyrantSensorConfig::HWT905_MOUNTING`

Changing the physical HWT905 orientation must only require changing
this mounting configuration. Estimator and control algorithms must continue
to receive FRD body-frame measurements.


## Yaw initialization and reference

The estimator must not automatically redefine the startup heading as
zero.

When a valid magnetic heading solution is available, internal yaw
represents that fused heading directly.

No runtime yaw-reference offset is applied by default.

A future operator/mission command may define the current heading as a
new control-reference zero without resetting the reduced yaw estimator.

Conceptually:

`yaw_relative = wrap(yaw_internal - yaw_reference_offset)`

The internal yaw estimator state remains unchanged.

The same runtime reference mechanism is intended for both MANUAL/remote
and AUTO operation. It is not implemented yet. The current shared controller
instead latches the current internal yaw as its held heading reference when
control becomes active and slews that reference with the yaw command; this
does not redefine the estimator's yaw zero.


## Yaw fusion

Gyroscope data is used for attitude/yaw propagation.

A new, healthy magnetometer measurement may be used for heading
correction.

Initialization requires stationary IMU samples and a valid magnetic heading.
After initialization, unavailable magnetic measurements do not stop gyro
propagation; the heading-valid flag expires when no usable heading correction
has arrived within the configured timeout.

Raw magnetometer values are not treated directly as yaw. Current heading
correction applies the configured mounting and calibration transforms, tilt
compensation, and finite/nonzero horizontal-field checks. It uses each new
`mag_sequence` once and wraps the yaw innovation before the Kalman update.
There is no magnetic-disturbance or innovation-magnitude rejection gate yet;
those checks and physical calibration remain further validation work.


## Disturbance estimation

The first Tyrant AUV estimator version does not include water-current
or external-disturbance states.

External disturbances are initially handled through closed-loop control using the reduced state. Reduced LMPC remains future work after verified geometry and thruster characterization, SysID data collection, model identification, and independent model validation with the available state feedback.

Explicit disturbance estimation may be considered later only after the
vehicle dynamic model has been sufficiently identified and validated.
