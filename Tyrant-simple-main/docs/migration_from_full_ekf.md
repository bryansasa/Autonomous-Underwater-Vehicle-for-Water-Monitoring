# Migration from `tyrant-auv`

## Keep the old repository

Do not delete `tyrant-auv`. It remains the full-EKF research archive and a source of validated subsystem implementations.

## Reused in this clean baseline

- HWT905/WIT driver.
- IMU mounting conversion.
- Sensor manager.
- Depth estimator and reference manager.
- Vehicle mode state machine.
- Safety heartbeat behavior.
- 4-state connection manager.
- Scheduler concept.

## Replaced

The full estimator tree is replaced by one module:

```text
include/estimation/simple_state_estimator.h
src/estimation/simple_state_estimator.cpp
```

No compatibility wrapper around the old EKF is kept.

## ROS migration

Removed conceptual outputs:

```text
/tyrant/state
/tyrant/estimator/health
```

New reduced output:

```text
/tyrant/simple_state
```

No dummy X/Y position or velocity is published.
