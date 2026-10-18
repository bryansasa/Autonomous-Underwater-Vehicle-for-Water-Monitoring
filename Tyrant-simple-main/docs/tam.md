# Tyrant Simple — TAM Foundation

The codebase now contains a tested TAM builder and a normalized damped least-squares allocator. Production thruster geometry is still intentionally absent, so the normal production-safe build does not enable allocation.

For thruster `i`, the allocation-matrix column is:

```text
B_i = [ d_i ; r_i × d_i ]
```

where:

- `r_i` is the thruster position vector in BODY FRD coordinates, metres, from the chosen body/control origin;
- `d_i` is the unit force direction for positive thruster force;
- BODY is `+X forward, +Y right/starboard, +Z down`.

The implementation normalizes `d_i` and rejects non-finite geometry or zero-length directions.

## Why the production matrix is not hard-coded yet

Tyrant requires the actual CAD geometry, final thruster numbering, direction convention, and measured actuator limits. A generic BlueROV-style matrix must not be substituted.

Before enabling allocation, fill one row per physical thruster in `docs/thruster_geometry_template.csv` and verify it against the assembled vehicle.

QP/constrained allocation comes after:

1. final `r_i` and `d_i` are frozen;
2. forward/reverse thrust curves are measured;
3. ESC neutral/deadzone is measured;
4. minimum/maximum thrust and failed-channel behavior are defined.


## Current allocator

The development allocator uses:

```text
u = B^T (B B^T + lambda^2 I)^-1 tau
```

followed by uniform scaling if any normalized thruster command exceeds the configured absolute limit. This preserves command direction while preventing individual normalized outputs from exceeding the development range. It is a software-validation allocator, not the final constrained/QP allocator.

`teensy41-mock-thrusters` enables an explicitly synthetic, full-rank geometry so the entire software path can be exercised before assembly. The default `teensy41` build does not use that geometry and remains fail-closed.

The final allocator is expected to incorporate measured forward/reverse thrust limits, deadzones, failed-channel constraints, and physical wrench units after characterization.
