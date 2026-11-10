"""Turn raw lap telemetry into a compact, verified fact sheet for the AI race engineer.

The LLM never sees raw telemetry. Everything it is allowed to quote is computed here with pandas,
from columns that are known to exist in the parquet files written by assetto_corsa_gym. The prompt
rules in GROUNDING_RULES then tell the model to use only these facts and to say when a question
needs data that is not in the sheet.

Notes on the data (checked against all 856 recorded runs):
* One parquet file = one training episode ("run"). An episode can cross the start/finish line
  several times, and AC's lap counter (`completedLaps`) and lap timer (`iLastTime`, ms) keep
  running across episodes and car resets. A lap time is therefore only trusted when the whole lap
  was driven inside this run, i.e. between two lap-counter increments in the same file.
* Track position is `NormalizedSplinePosition` (0 = start/finish line, 1 = end of lap).
* An episode ends because the car left the track (`out_of_track`), the environment stopped it for
  being too slow (`terminated`), or it hit the step limit (`TimeLimit.truncated`).
"""

import pandas as pd

MONZA_CORNERS = [
    {"name": "Variante del Rettifilo (Turn 1 Chicane)", "start": 0.00, "end": 0.12},
    {"name": "Curva Grande (Turn 3)", "start": 0.12, "end": 0.28},
    {"name": "Variante della Roggia (Turn 4 Chicane)", "start": 0.28, "end": 0.45},
    {"name": "Lesmo Curves (Turns 6-7)", "start": 0.45, "end": 0.65},
    {"name": "Variante Ascari (Turn 8 Chicane)", "start": 0.65, "end": 0.82},
    {"name": "Curva Parabolica (Turn 11)", "start": 0.82, "end": 1.00},
]

POS = "NormalizedSplinePosition"
LAUNCH_SPEED = 10.0  # m/s
TYRES = {"FL": "fl", "FR": "fr", "RL": "rl", "RR": "rr"}

# Columns the fact sheet needs (read in addition to whatever the charts need).
CONTEXT_COLS = [
    "speed", "accelY", "accStatus", "brakeStatus", "reward",
    POS, "completedLaps", "iLastTime", "out_of_track", "terminated", "TimeLimit.truncated",
] + [f"{w}_tire_temperature_core" for w in TYRES.values()] \
  + [f"tyre_slip_ratio_{w}" for w in TYRES.values()]


def corner_of(pos):
    for corner in MONZA_CORNERS:
        if corner["start"] <= pos < corner["end"]:
            return corner["name"]
    return MONZA_CORNERS[-1]["name"] if pos >= 1.0 else "Unknown section"


def _has(df, *cols):
    return all(c in df.columns for c in cols) and len(df) > 0


def lap_times(df):
    """Lap times (seconds) for laps driven completely inside this run."""
    if not _has(df, "completedLaps", "iLastTime"):
        return []
    laps = df["completedLaps"].to_numpy()
    crossings = [i for i in range(1, len(laps)) if laps[i] > laps[i - 1]]
    # The first crossing finishes a lap that started before this run (or before a reset): skip it.
    return [float(df["iLastTime"].iloc[i]) / 1000.0 for i in crossings[1:] if df["iLastTime"].iloc[i] > 0]


def end_reason(df):
    """(reason, corner) explaining why the run stopped, from the final frame."""
    if not len(df):
        return "no data", None
    last = df.iloc[-1]
    corner = corner_of(float(last[POS])) if POS in df.columns else None
    if "out_of_track" in df.columns and last["out_of_track"] > 0:
        return "left the track", corner
    if "TimeLimit.truncated" in df.columns and bool(last["TimeLimit.truncated"]):
        return "reached the episode time limit", corner
    if "terminated" in df.columns and bool(last["terminated"]):
        return "stopped for being too slow (stalled or spun)", corner
    return "still running or stopped for another reason", corner


def fmt_lap(seconds):
    return f"{int(seconds // 60)}:{seconds % 60:06.3f}" if seconds else "none"


def run_facts(df):
    """Small per-run summary used for history lines, charts and the fact sheet."""
    laps = lap_times(df)
    reason, corner = end_reason(df)
    return {
        "frames": int(len(df)),
        "laps": laps,
        "best_lap": min(laps) if laps else None,
        "peak": float(df["speed"].max()) if _has(df, "speed") else None,
        "mean": float(df["speed"].mean()) if _has(df, "speed") else None,
        "max_g": float(df["accelY"].abs().max()) if _has(df, "accelY") else None,
        "off": reason == "left the track",
        "end_reason": reason,
        "end_corner": corner,
        "reward": float(df["reward"].sum()) if _has(df, "reward") else float(len(df)),
    }


def _num(v, fmt="{:.1f}"):
    return fmt.format(v) if v is not None and pd.notna(v) else "n/a"


def corner_table(df):
    """One line per Monza section the car drove through in this run.

    Frames before the car first reaches LAUNCH_SPEED are left out, so the standing start after a
    reset does not show up as a 0 m/s corner.
    """
    if not _has(df, POS, "speed"):
        return ["(track position not recorded)"]
    moving = df["speed"] > LAUNCH_SPEED
    if not moving.any():
        return ["- the car never got above launch speed in this run"]
    df = df.loc[moving.idxmax():]
    sec = df[POS].apply(corner_of)
    lines = []
    for corner in MONZA_CORNERS:
        part = df[sec == corner["name"]]
        if part.empty:
            lines.append(f"- {corner['name']}: not reached in this run")
            continue
        brake = part["brakeStatus"].max() if "brakeStatus" in part else None
        thr = part["accStatus"].mean() if "accStatus" in part else None
        g = part["accelY"].abs().max() if "accelY" in part else None
        lines.append(
            f"- {corner['name']}: min speed {_num(part['speed'].min())} m/s, "
            f"max speed {_num(part['speed'].max())} m/s, peak brake {_num(brake, '{:.2f}')}, "
            f"avg throttle {_num(thr, '{:.2f}')}, max G {_num(g, '{:.2f}')}"
        )
    return lines


def tyre_lines(df):
    lines = []
    for label, w in TYRES.items():
        t, s = f"{w}_tire_temperature_core", f"tyre_slip_ratio_{w}"
        if _has(df, t) or _has(df, s):
            lines.append(
                f"- {label}: core temp avg {_num(df[t].mean() if t in df else None)} C "
                f"(max {_num(df[t].max() if t in df else None)} C), "
                f"slip ratio avg {_num(df[s].abs().mean() if s in df else None, '{:.3f}')}"
            )
    return lines or ["(tyre data not recorded)"]


def history_line(number, facts):
    best = fmt_lap(facts["best_lap"]) if facts["best_lap"] else "none"
    where = f" at {facts['end_corner']}" if facts["end_corner"] else ""
    return (f"- Run #{number}: best full lap: {best} | peak {_num(facts['peak'])} m/s | "
            f"avg {_num(facts['mean'])} m/s | ended: {facts['end_reason']}{where}")


def build_fact_sheet(df, number, total_runs, history):
    """history: list of (run number, facts) for earlier runs, newest first."""
    f = run_facts(df)
    laps = ", ".join(fmt_lap(x) for x in f["laps"]) or "none (no lap was driven start-to-finish within this run)"
    where = f" at {f['end_corner']}" if f["end_corner"] else ""

    hist = [h for h in history if h[1] is not None]
    off_counts = {}
    for _, h in hist:
        if h["off"] and h["end_corner"]:
            off_counts[h["end_corner"]] = off_counts.get(h["end_corner"], 0) + 1
    off_summary = ", ".join(f"{c}: {n}" for c, n in sorted(off_counts.items(), key=lambda x: -x[1])) or "none"
    bests = [h["best_lap"] for _, h in hist if h["best_lap"]]

    return "\n".join([
        f"[SELECTED RUN: Run #{number} of {total_runs} in this view]",
        f"- Frames recorded: {f['frames']}",
        f"- Full laps completed inside this run: {len(f['laps'])} (times: {laps})",
        f"- Peak speed: {_num(f['peak'])} m/s, average speed: {_num(f['mean'])} m/s",
        f"- Max cornering G: {_num(f['max_g'], '{:.2f}')}",
        f"- How the run ended: {f['end_reason']}{where}",
        "",
        "[SELECTED RUN: BY TRACK SECTION] (from the moment the car first passed 10 m/s)",
        *corner_table(df),
        "",
        "[SELECTED RUN: TYRES]",
        *tyre_lines(df),
        "",
        f"[PREVIOUS {len(hist)} RUNS, NEWEST FIRST]",
        *([history_line(n, h) for n, h in hist] or ["- none: this is the first run in this view"]),
        f"- Where those runs left the track (count): {off_summary}",
        f"- Best full lap among them: {fmt_lap(min(bests)) if bests else 'none'}",
        "",
        "[NOT IN THE DATA] steering inputs per corner, racing line, setup, weather, fuel, damage, "
        "other cars, sector times, and any run not listed above.",
    ])


GROUNDING_RULES = """\
Rules you must follow:
1. Use ONLY the facts in the DATA block. Never invent, estimate or calculate new numbers, lap times,
   corners or run numbers that are not written there.
2. Quote numbers exactly as written in the DATA block, with their units.
3. If the question needs information that is not in the DATA block, say plainly that the dashboard
   does not have that data, then answer only the part you can, and suggest what to look at instead.
4. "Full laps" only counts laps driven start-to-finish inside one run. If there are none, say the
   driver has not completed a full lap in that run; do not make up a lap time.
5. Refer to runs by their "Run #" number. Refer to the AI model as "the driver".
"""
