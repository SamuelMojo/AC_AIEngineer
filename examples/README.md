# Example telemetry

`monza_full_lap.parquet` is a real sample of what Assetto Corsa and the
[assetto_corsa_gym](https://github.com/dasGringuen/assetto_corsa_gym) environment record. It is
**one full lap of Monza (2:01.260)** in a BMW Z4 GT3 (as set in `config.yml`), driven by the reinforcement-learning agent and recorded at 25 frames a second.

| | (as above) |
|---|---|
| Frames | 3,032 (about 121 seconds) |
| Columns | 110 |
| Size | 2.1 MB (zstd-compressed Parquet) |
| Source | Run #233 of the 30 Oct 2026 training session (a 15,002-frame episode), cut down to the frames between two start/finish-line crossings |

During training, every episode is written as a file like this (one row per frame). A full training
run is up to 15,000 rows, and my local `outputs/` folder holds 856 such files. This is why the AI
engineer is given a short summary instead of the raw data (see [how the AI engineer
works](../docs/ai_engineer.md#0-where-it-started-letting-the-ai-read-everything)).

## Open it

```python
import pandas as pd

df = pd.read_parquet("examples/monza_full_lap.parquet")
print(df.shape)                                   # (3032, 110)
print(df[["currentTime", "speed", "accStatus", "brakeStatus", "NormalizedSplinePosition"]].head())

df["speed"].plot()                                # speed trace for the lap (needs matplotlib)
```

Parquet is a compact, column-based format, so you can read only the columns you need. That is how
the dashboard keeps its S3 reads fast. The file needs `pyarrow` (already in `requirements.txt`).

## What is in it

Columns marked \* are the ones the dashboard uses. Ranges are the minimum and maximum over this lap.
Where the table gives no meaning, the column is recorded as it comes from the game and the
environment. Units are given only where they are clear from the data.

### Car motion

How the car is moving through space.

| Column | Range in this lap | Meaning |
|---|---|---|
| * `speed` | 13.39 … 70.82 | Speed (m/s) |
| `local_velocity_x` | 13.39 … 70.82 | Velocity in the car's own frame (this axis matches `speed`) |
| `local_velocity_y` | -5.837 … 5.236 | (as above) |
| `local_velocity_z` | -0.4945 … 0.7258 | (as above) |
| `velocity_x` | -49.16 … 66.93 | Velocity in world coordinates |
| `velocity_y` | -1.569 … 1.428 | (as above) |
| `velocity_z` | -70.55 … 66.93 | (as above) |
| `accelX` | -1.997 … 1.68 | Acceleration, x axis (G) |
| * `accelY` | -1.886 … 1.103 | Acceleration, y axis (G); the dashboard reads this one as cornering G |
| `angular_velocity_x` | -0.1578 … 0.1784 | Rotation rates |
| `angular_velocity_y` | -0.894 … 1.057 | (as above) |
| `angular_velocity_z` | -0.2882 … 0.4752 | (as above) |
| `yaw` | -3.141 … 3.141 | Car orientation (rad) |
| `pitch` | -0.02813 … 0.0269 | (as above) |
| `roll` | -0.05924 … 0.03833 | (as above) |
| `world_position_x` | -1277 … 889.4 | Position on the map (m) |
| `world_position_y` | -211.6 … 1046 | (as above) |
| `world_position_z` | -11.07 … 1.705 | (as above) |

### Driver inputs and drivetrain

What the car is being told to do, and how the engine responds.

| Column | Range in this lap | Meaning |
|---|---|---|
| * `accStatus` | 0 … 1 | Throttle, 0–1 |
| * `brakeStatus` | 0 … 1 | Brake, 0–1 |
| `steerAngle` | -298.1 … 299.6 | Steering wheel angle |
| `actualGear` | 1 … 7 | Current gear |
| `RPM` | 2892 … 8718 | Engine speed |
| `LastFF` | 0.00022 … 1.199 | Force-feedback level |

### Lap and position

Where the car is on the lap, and the game's own timing.

| Column | Range in this lap | Meaning |
|---|---|---|
| * `NormalizedSplinePosition` | 0.0003981 … 0.9999 | Position around the lap, 0 = start/finish line, 1 = back at the line |
| `LapDist` | 2.292 … 5758 | Distance covered this lap (m) |
| `LapCount` | 26 … 27 | Current lap number |
| * `completedLaps` | 26 (constant) | Laps completed. Keeps counting across car resets, so lap times need care |
| `currentTime` | 0.009 … 121.2 | Time into the current lap (s) |
| * `iLastTime` | 1.213e+05 … 2.481e+05 | Last completed lap time (ms) |
| `BestLap` | 1.213e+05 … 1.24e+05 | Best lap time so far (ms) |
| `LapInvalidated` | 0 (constant) | Lap invalidated flag |
| `penaltyTime` | 0 (constant) | Penalty time |
| `isInPit` | 0 (constant) | In the pit lane |

### Tyres

Four wheels, FL = front-left, FR = front-right, RL = rear-left, RR = rear-right.

| Column | Range in this lap | Meaning |
|---|---|---|
| * `fl_tire_temperature_core` | 84.38 … 100.7 | Tyre core temperature (°C) |
| * `fr_tire_temperature_core` | 77.86 … 99.2 | Tyre core temperature (°C) |
| * `rl_tire_temperature_core` | 61.03 … 67.12 | Tyre core temperature (°C) |
| * `rr_tire_temperature_core` | 56.3 … 60.52 | Tyre core temperature (°C) |
| `fl_tire_pressure` | 25.34 … 27.96 | Tyre pressure |
| `fr_tire_pressure` | 24.3 … 27.71 | Tyre pressure |
| `rl_tire_pressure` | 21.6 … 22.58 | Tyre pressure |
| `rr_tire_pressure` | 20.85 … 21.52 | Tyre pressure |
| `fl_wheel_load` | 0 … 1.012e+04 | Load on the wheel |
| `fr_wheel_load` | 0 … 9992 | Load on the wheel |
| `rl_wheel_load` | 0 … 9604 | Load on the wheel |
| `rr_wheel_load` | 506.6 … 8841 | Load on the wheel |
| * `tyre_slip_ratio_fl` | -1 … 0.007502 | Slip ratio: how much the tyre is spinning or locking relative to the road |
| * `tyre_slip_ratio_fr` | -1.001 … 0.005998 | Slip ratio: how much the tyre is spinning or locking relative to the road |
| * `tyre_slip_ratio_rl` | -0.2948 … 0.2432 | Slip ratio: how much the tyre is spinning or locking relative to the road |
| * `tyre_slip_ratio_rr` | -0.2209 … 0.1995 | Slip ratio: how much the tyre is spinning or locking relative to the road |
| `SlipAngle_fl` | -15.93 … 21.38 | Slip angle |
| `SlipAngle_fr` | -18.24 … 19.1 | Slip angle |
| `SlipAngle_rl` | -6.759 … 17.44 | Slip angle |
| `SlipAngle_rr` | -7.112 … 17.01 | Slip angle |
| `Dy_fl` | 0 … 2.697 | Lateral grip coefficient |
| `Dy_fr` | 0 … 2.797 | Lateral grip coefficient |
| `Dy_rl` | 0 … 1.929 | Lateral grip coefficient |
| `Dy_rr` | 1.138 … 1.977 | Lateral grip coefficient |
| `wheel_speed_fl` | 1.791e-25 … 207.8 | Wheel rotation speed (rad/s) |
| `wheel_speed_fr` | 1.349e-32 … 207.6 | Wheel rotation speed (rad/s) |
| `wheel_speed_rl` | 36.43 … 203.2 | Wheel rotation speed (rad/s) |
| `wheel_speed_rr` | 39.18 … 203.2 | Wheel rotation speed (rad/s) |
| `tyreContactHeading_FL_x` | -1 … 1 | Direction of the tyre contact patch |
| `tyreContactHeading_FL_y` | -0.07984 … 0.239 | Direction of the tyre contact patch |
| `tyreContactHeading_FL_z` | -1 … 1 | Direction of the tyre contact patch |
| `tyreContactHeading_FR_x` | -1 … 1 | Direction of the tyre contact patch |
| `tyreContactHeading_FR_y` | -0.05612 … 0.03065 | Direction of the tyre contact patch |
| `tyreContactHeading_FR_z` | -1 … 1 | Direction of the tyre contact patch |
| `tyreContactHeading_RL_x` | -1 … 1 | Direction of the tyre contact patch |
| `tyreContactHeading_RL_y` | -0.08797 … 0.2747 | Direction of the tyre contact patch |
| `tyreContactHeading_RL_z` | -1 … 1 | Direction of the tyre contact patch |
| `tyreContactHeading_RR_x` | -1 … 1 | Direction of the tyre contact patch |
| `tyreContactHeading_RR_y` | -0.05584 … 0.03108 | Direction of the tyre contact patch |
| `tyreContactHeading_RR_z` | -1 … 1 | Direction of the tyre contact patch |
| `CamberRad` | 4 values per frame | Camber, one value per wheel |
| `Mz` | 4 values per frame | Self-aligning torque, one value per wheel |
| `NdSlip` | 4 values per frame | Normalised slip, one value per wheel |
| `tyres_load` | 4 values per frame | Load, one value per wheel |
| `tyre_loaded_radius` | 4 values per frame | Loaded radius, one value per wheel |
| `dynamic_pressure` | 4 values per frame | One value per wheel |

### Suspension

| Column | Range in this lap | Meaning |
|---|---|---|
| `fl_damper_linear_potentiometer` | 0.00885 … 0.04756 | Damper position |
| `fr_damper_linear_potentiometer` | 0.007654 … 0.04427 | Damper position |
| `rl_damper_linear_potentiometer` | 0.0158 … 0.07271 | Damper position |
| `rr_damper_linear_potentiometer` | 0.01849 … 0.07071 | Damper position |
| `SuspensionTravel` | 4 values per frame | Suspension travel, one value per wheel |
| `cgHeight` | 0.3586 … 0.3954 | Centre-of-gravity height |

### Track limits

Whether the car is on the track, and how close it is to the edge.

| Column | Range in this lap | Meaning |
|---|---|---|
| * `out_of_track` | 0 (constant) | 1 when the car is judged off the track (used to end a run) |
| `out_of_track_ac` | 0 (constant) | Off-track flag from Assetto Corsa itself |
| `out_of_track_calc` | 0 (constant) | Off-track flag calculated by the environment |
| `numberOfTyresOut` | 0 (constant) | Number of tyres outside the track limits |
| `dist_to_border` | 0.8803 … 5.739 | Distance to the track edge (m) |
| `going_backwards` | 0 (constant) | Car is travelling the wrong way |
| `gap` | -3.54 … 3.708 | Gap to the reference racing line |
| `rl_point` | -1 … 3748 | Index of the nearest racing-line point |
| `sensors` | 11 values per frame | 11 ray-cast sensor readings the agent 'sees' each frame |

### Reinforcement-learning episode

What the training environment records about the agent.

| Column | Range in this lap | Meaning |
|---|---|---|
| * `reward` | 0.1479 … 0.8401 | Reward the agent received this step |
| `done` | 0 (constant) | Episode ended on this step |
| * `terminated` | true/false | Episode stopped by the environment (e.g. too slow) |
| * `TimeLimit.truncated` | true/false | Episode hit the time or lap limit |
| `actions_0` | -0.9999 … 0.9994 | The agent's 3 control outputs, scaled −1 to 1 |
| `actions_1` | -0.9988 … 0.9999 | (as above) |
| `actions_2` | -1 … 0.9926 | (as above) |
| `current_action_abs_0` | -0.6625 … 0.6658 | The same actions after conversion |
| `current_action_abs_1` | -1 … 1 | (as above) |
| `current_action_abs_2` | -1 … 1 | (as above) |
| `steps` | 3480 … 6511 | Environment step counter |

### Bookkeeping

| Column | Range in this lap | Meaning |
|---|---|---|
| `packetId` | 1.293e+06 … 1.305e+06 | Game packet counter |
| `timestamp_ac` | 1.293e+04 … 1.306e+04 | Game timestamp |
| `timestamp_env` | 1.367e+04 … 1.379e+04 | Environment timestamp |
| `total_errors_out_of_sync` | 0 (constant) | Sync errors between game and environment |

## Notes on reading the data

- **One file is one episode, not one lap.** An episode can cross the start/finish line several
  times, or end after a few seconds if the car leaves the track. This sample is trimmed to one
  clean lap.
- **The lap counter and lap timer keep running across car resets,** so `iLastTime` on its own can
  report a "lap" that spans a reset (this sample's first row still carries the 4:08.072 from the
  lap before it). The dashboard only counts a lap time when the whole lap was driven inside one file.
- **Corner names are not in the data.** The game only records position around the lap
  (`NormalizedSplinePosition`); the dashboard maps that to Monza corner names itself.
- **Not every column varies.** A few, such as `LapInvalidated`, `penaltyTime` and the three
  off-track flags, are constant here because this was a clean lap.
