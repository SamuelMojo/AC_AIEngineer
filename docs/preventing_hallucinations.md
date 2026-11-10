# Update: stopping the AI race engineer from making things up

**Date:** 10 Nov 2026
**Files:** `telemetry_context.py` (new), `dashboard_v2.py`

## The problem

The dashboard's AI race engineer (Llama 3.1 via Ollama) gave confident, specific answers that
turned out to be invented. In one session the automated brief reported a **lap time of 2:35.71**
and said the driver left the track **at the Lesmo curves five times out of the last ten runs**.
In the pit radio chat it claimed the car reached **54.6 m/s in the Parabolica**.

None of those numbers existed in the data the model was given.

## Root cause

There were two separate faults, and they made each other worse.

**1. The data handed to the model was wrong.** The prompt was built from columns that don't exist
in the telemetry files. The code looked for `lap_time`, `lap_duration` or `lapTime` to report
lap times and for `progress` to work out where the car left the track. I checked all 856
recorded runs across 7 training sessions: none of those columns exist. Lap timing is stored in
`completedLaps` and `iLastTime`, and track position in `NormalizedSplinePosition`. So for
**every** run, the model was told "lap time: Not Completed" and "off-track corner: None".

**2. The prompt pushed the model to fill the gap.** It told the model to *"always include
exact numbers, stats and figures"* and to *"use real Monza corner names"*. With no real lap time
or corner in front of it, the model did what it was asked and produced plausible-looking ones.
The context also only held a few headline numbers, so any question beyond them (braking,
corners, tyres) had no data behind it at all.

A third, smaller issue: the automated brief sent its whole prompt as a `system` message with no
`user` message. Llama sometimes reacts by printing its own role label, which is why the brief
started with the word "assistant".

## Investigating the real data

Fixing the column names wasn't enough on its own, because the lap counter doesn't behave the
way you'd expect:

- One parquet file is one training **episode**, not one lap. An episode can cross the
  start/finish line several times.
- Assetto Corsa's lap counter and lap timer keep running **across** episodes and car resets.
  Taking `iLastTime` at face value produced "lap times" of over 31 minutes.
- A lap time is only real if the whole lap was driven inside one episode, between two lap-counter
  increments in the same file.

With that rule, the data shows the agent has driven **16 genuine full laps in 8 of 856 runs**,
with a best of **1:59.802**. The old dashboard reported none of them. Every episode ends for
one of three recorded reasons: the car left the track (669 runs), the environment stopped it for
being too slow (176), or it hit the time limit (5). Six were still running or were stopped
another way.

## The fix

### 1. A verified fact sheet (`telemetry_context.py`)
All the numbers the model may quote are now computed with pandas, in one testable module, from
columns confirmed to exist. For the selected run the model now gets:
- full laps driven inside the run, with their times
- peak and average speed, max cornering G
- **how and where the run ended** (left the track / too slow / time limit, plus the corner)
- a **per-corner table** for all six Monza sections: min/max speed, peak brake, average
  throttle and max G. The standing start after a reset is left out so it doesn't show as a
  0 m/s corner.
- tyre core temperatures and slip ratios for all four corners of the car
- the previous 10 runs, each with its best full lap and how and where it ended, plus a count of
  where those runs left the track
- an explicit **"not in the data"** list (steering per corner, racing line, setup, weather,
  sector times…), so the model knows what it can't answer

Runs are numbered **Run #1, #2, …** in the same order as the dashboard's reward chart, so any
run the model mentions can be checked on screen.

### 2. Grounding rules in every prompt
The "always include numbers" instruction is gone. Both the automated brief and the pit radio
now share these rules:
1. Use only the facts in the DATA block; never invent, estimate or calculate new numbers.
2. Quote numbers exactly as written, with units.
3. If a question needs data that isn't there, say so plainly, answer what you can, and suggest
   what to look at.
4. Only quote a lap time if a full lap is listed.
5. Refer to runs by their Run # number.

### 3. Less room for creativity
- Temperature lowered to 0.2 for both the brief and the chat.
- The brief now sends instructions as a `system` message and the data as a `user` message,
  and any leading "assistant" label is stripped.

## How it was tested
I ran the dashboard's real prompt-building code against the 239 recorded runs from the
30 Oct session, with S3 and Ollama swapped for local stubs, and checked the exact messages sent
to the model. For example, Run #233's fact sheet lists three full laps (2:01.260, 2:01.977,
2:00.338). The last of these matches the lap time recorded by the game itself (`iLastTime`,
120,338 ms).

## Known limits and next steps
- **Corner boundaries need calibrating.** The Monza section map says the Turn 1 chicane is at
  0–12% of the lap, but the car never drops below 62 m/s there and brakes hard (to 13 m/s) in the
  12–28% section. The boundaries should be redrawn from the track's spline data.
- An 8B model can still occasionally ignore its instructions. The next step is **tool calling**:
  give the model functions such as `get_corner_stats(run, corner)` and `compare_runs(a, b)`, so
  it fetches exactly the data a question needs instead of relying on a fixed summary.
- The v1 terminal tools (`legacy/race_engineer.py`, `legacy/pit_radio.py`) still use their original
  summaries.
