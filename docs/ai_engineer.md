# How the AI race engineer works

The dashboard has two AI features, both powered by **Llama 3.1** running locally through
**Ollama** on the training PC's GPU:

- **Automated Engineer Brief**: a one-click, two-sentence debrief of the selected run.
- **Pit Radio Channel**: a chat box where you can ask follow-up questions.

Both use the same pipeline: **raw telemetry → verified fact sheet → prompt with grounding rules →
Llama 3.1**. The model never sees raw telemetry, only the fact sheet. (It didn't start that way:
see [section 0](#0-where-it-started-letting-the-ai-read-everything).)

Code: [`telemetry_context.py`](../telemetry_context.py) builds the fact sheet and rules;
[`dashboard_v2.py`](../dashboard_v2.py) builds the prompts and talks to Ollama.

---

## 0. Where it started: letting the AI read everything

The first version of this project gave the model the telemetry itself. The idea was simple: the
data is all there, so let the AI scan it and work out what happened. It didn't work, for three
reasons.

**It was far too much data.** One training run is a parquet file with around 100 columns and up to
15,000 rows. That is roughly 1.5 million numbers for a single run, before counting the previous
runs the engineer was meant to compare it with. That is many times more than a language model
can hold at once, and by default Ollama quietly cuts off whatever doesn't fit. So the model
was often answering from only the start of a run, without saying so.

**It was very slow.** Every question meant loading, formatting and sending a huge block of text,
and then waiting for the model to read all of it before it wrote a single word. On a live
dashboard that is unusable.

**It was pointless, even when it fit.** Language models are poor at reading thousands of rows of
numbers. They can't reliably find a maximum, count off-track events or compare two runs by
scanning raw values. A few lines of pandas do that exactly and instantly. The model's real job is
what it is good at: explaining findings in plain English.

**The change:** split the work. pandas does the maths and produces a short, verified fact sheet,
and the model only turns that into language. The fact sheet is about 1,000 tokens instead of
millions, answers arrive quickly, and every number can be checked. It was the first step toward
the grounding approach described in
[preventing_hallucinations.md](preventing_hallucinations.md).

> **Rule of thumb from this project:** use code for calculation and the LLM for explanation.

---

## 1. From telemetry to fact sheet

Each training run is one parquet file with roughly 100 columns and up to 15,000 rows (25 frames a
second). Sending that to a language model would be slow, expensive in tokens and invite
guesswork. Instead, `build_context()` loads the selected run and the 10 runs before it, and
`telemetry_context.build_fact_sheet()` uses pandas to compute:

| Section | What it contains |
|---|---|
| Selected run | Frames, full laps driven inside the run (and their times), peak/average speed, max G, how and where the run ended |
| By track section | For each of the six Monza sections: min/max speed, peak brake, average throttle, max G (standing start excluded) |
| Tyres | Core temperature (avg/max) and average slip ratio for each wheel |
| Previous 10 runs | Best full lap, speeds and how/where each ended, plus where they left the track and the best lap among them |
| Not in the data | Things the model must say it can't answer (setup, racing line, sector times…) |

Runs are numbered **Run #1 = oldest**, matching the reward chart, so anything the model says can
be checked on screen. Why lap times need special handling (the game's lap timer keeps running
across car resets) is explained in [preventing_hallucinations.md](preventing_hallucinations.md).

---

## 2. Automated Engineer Brief

Triggered by **Generate AI Debrief for Selected Run** (`generate_summary_text()`).

### The request sent to Ollama

The `ollama` Python client sends one JSON request to Ollama's `/api/chat` endpoint. The telemetry
travels as **plain text inside the message content**, not as JSON: it is shorter, reads like a
briefing, and small models handle it more reliably.

```json
{
  "model": "llama3.1:latest",
  "stream": false,
  "keep_alive": "30m",
  "options": { "temperature": 0.2 },
  "messages": [
    { "role": "system", "content": "<instructions + grounding rules>" },
    { "role": "user",   "content": "DATA:\n<fact sheet>\n\nWrite the 2-sentence debrief." }
  ]
}
```

- `temperature: 0.2`: low randomness, so the model sticks to the facts.
- `keep_alive: "30m"`: keeps the model loaded in GPU memory so the next request is fast.

### The system message (same for every run)

```
You are an R&D simulation engineer explaining how an AI driving model is learning.
Write a simple, clear 2-sentence summary in everyday language for non-technical readers.
Start directly with the analysis (no "Sure", no "Here is a summary").
Mention the full lap time only if one is listed, how the run ended and where, and how it compares
with the previous runs.

Rules you must follow:
1. Use ONLY the facts in the DATA block. Never invent, estimate or calculate new numbers, lap times,
   corners or run numbers that are not written there.
2. Quote numbers exactly as written in the DATA block, with their units.
3. If the question needs information that is not in the DATA block, say plainly that the dashboard
   does not have that data, then answer only the part you can, and suggest what to look at instead.
4. "Full laps" only counts laps driven start-to-finish inside one run. If there are none, say the
   driver has not completed a full lap in that run; do not make up a lap time.
5. Refer to runs by their "Run #" number. Refer to the AI model as "the driver".
```

### The user message (changes per run)

A real example from the 30 Oct training session:

```
DATA:
[SELECTED RUN: Run #233 of 239 in this view]
- Frames recorded: 15002
- Full laps completed inside this run: 3 (times: 2:01.260, 2:01.977, 2:00.338)
- Peak speed: 70.8 m/s, average speed: 47.1 m/s
- Max cornering G: 2.11
- How the run ended: reached the episode time limit at Variante Ascari (Turn 8 Chicane)

[SELECTED RUN: BY TRACK SECTION] (from the moment the car first passed 10 m/s)
- Variante del Rettifilo (Turn 1 Chicane): min speed 61.9 m/s, max speed 70.8 m/s, peak brake 0.39, avg throttle 0.74, max G 0.49
- Curva Grande (Turn 3): min speed 13.4 m/s, max speed 70.8 m/s, peak brake 1.00, avg throttle 0.69, max G 2.11
- Variante della Roggia (Turn 4 Chicane): min speed 17.5 m/s, max speed 68.0 m/s, peak brake 1.00, avg throttle 0.70, max G 1.83
- Lesmo Curves (Turns 6-7): min speed 29.8 m/s, max speed 67.3 m/s, peak brake 0.92, avg throttle 0.81, max G 1.63
- Variante Ascari (Turn 8 Chicane): min speed 22.8 m/s, max speed 67.0 m/s, peak brake 1.00, avg throttle 0.80, max G 1.76
- Curva Parabolica (Turn 11): min speed 10.2 m/s, max speed 67.4 m/s, peak brake 1.00, avg throttle 0.92, max G 1.53

[SELECTED RUN: TYRES]
- FL: core temp avg 89.4 C (max 103.8 C), slip ratio avg 0.042
- FR: core temp avg 87.5 C (max 102.4 C), slip ratio avg 0.049
- RL: core temp avg 65.6 C (max 84.4 C), slip ratio avg 0.026
- RR: core temp avg 60.1 C (max 82.0 C), slip ratio avg 0.028

[PREVIOUS 10 RUNS, NEWEST FIRST]
- Run #232: best full lap: none | peak 70.6 m/s | avg 47.0 m/s | ended: left the track at Curva Parabolica (Turn 11)
- Run #231: best full lap: none | peak 71.7 m/s | avg 47.1 m/s | ended: left the track at Variante della Roggia (Turn 4 Chicane)
- Run #230: best full lap: none | peak 67.1 m/s | avg 46.2 m/s | ended: left the track at Variante della Roggia (Turn 4 Chicane)
- Run #229: best full lap: none | peak 71.1 m/s | avg 46.5 m/s | ended: left the track at Curva Parabolica (Turn 11)
- Run #228: best full lap: none | peak 71.4 m/s | avg 46.7 m/s | ended: left the track at Variante della Roggia (Turn 4 Chicane)
- Run #227: best full lap: none | peak 68.4 m/s | avg 46.3 m/s | ended: left the track at Variante della Roggia (Turn 4 Chicane)
- Run #226: best full lap: none | peak 23.8 m/s | avg 13.9 m/s | ended: left the track at Curva Grande (Turn 3)
- Run #225: best full lap: 2:04.940 | peak 72.0 m/s | avg 46.7 m/s | ended: left the track at Curva Grande (Turn 3)
- Run #224: best full lap: none | peak 72.4 m/s | avg 46.2 m/s | ended: left the track at Curva Parabolica (Turn 11)
- Run #223: best full lap: none | peak 67.6 m/s | avg 44.1 m/s | ended: left the track at Curva Parabolica (Turn 11)
- Where those runs left the track (count): Curva Parabolica (Turn 11): 4, Variante della Roggia (Turn 4 Chicane): 4, Curva Grande (Turn 3): 2
- Best full lap among them: 2:04.940

[NOT IN THE DATA] steering inputs per corner, racing line, setup, weather, fuel, damage, other cars, sector times, and any run not listed above.

Write the 2-sentence debrief.
```

### What happens to the reply
- Any stray `assistant` label at the start is removed (`clean_reply()`).
- The text is shown in the brief box and saved to `<run file>.summary.txt`, so the brief is still
  there next time that run is opened, without calling the model again.

---

## 3. Pit Radio Channel (chat box)

Handled by `render_chat()`. Step by step:

1. **You send a message.** `st.chat_input` captures it; it's added to the chat memory
   (`st.session_state.messages`) and shown immediately.
2. **The fact sheet is rebuilt** for the run currently selected, so if training is live and a new
   run arrives between two questions, the second answer uses the newer data.
3. **The prompt is assembled:**
   - one `system` message: the pit radio role, the grounding rules and the DATA block
   - the **last 10 chat messages**, alternating `user` / `assistant`, ending with your new
     question. This is what makes follow-ups like "why?" or "and the run before?" work.
4. **It's sent to Ollama** on the GPU PC (address from `AC_OLLAMA_URL`) with `stream: true`,
   `temperature 0.2` and `keep_alive 30m`.
5. **The reply streams in word by word** (`st.write_stream`), is cleaned with `clean_reply()`,
   and saved to the chat memory.
6. **Status line:** every 20 seconds the dashboard checks whether Ollama is reachable and shows
   "Engineer online" or "Engineer offline". If a request fails, a "Radio error" message appears
   instead of the page crashing.

### The request sent to Ollama

```json
{
  "model": "llama3.1:latest",
  "stream": true,
  "keep_alive": "30m",
  "options": { "temperature": 0.2 },
  "messages": [
    { "role": "system",    "content": "<pit radio instructions + grounding rules + DATA>" },
    { "role": "user",      "content": "why does he keep crashing?" },
    { "role": "assistant", "content": "In the last 10 runs the driver left the track at ..." },
    { "role": "user",      "content": "what are the tyre temps like?" }
  ]
}
```

### The system message

```
You are a helpful R&D simulation engineer explaining training progress over the pit radio.
Answer in clear, simple language, in a few short sentences. Use Monza corner names from the data.

Rules you must follow:
1. Use ONLY the facts in the DATA block. Never invent, estimate or calculate new numbers, lap times,
   corners or run numbers that are not written there.
2. Quote numbers exactly as written in the DATA block, with their units.
3. If the question needs information that is not in the DATA block, say plainly that the dashboard
   does not have that data, then answer only the part you can, and suggest what to look at instead.
4. "Full laps" only counts laps driven start-to-finish inside one run. If there are none, say the
   driver has not completed a full lap in that run; do not make up a lap time.
5. Refer to runs by their "Run #" number. Refer to the AI model as "the driver".
DATA:
<the same fact sheet as above>
```

### Things to know
- **Chat memory is per browser tab.** Refreshing the page clears it, and other viewers don't see
  your conversation.
- **The chat loads before the charts.** It's drawn first and isn't touched by auto-refresh, so
  you can type straight away and a refresh never interrupts an answer.
- **"I don't have that data" is expected.** Questions about things in the "not in the data" list,
  like setup or racing line, should get that answer instead of a guess.

---

## 4. How the brief and the chat differ

| | Automated Engineer Brief | Pit Radio Channel |
|---|---|---|
| Triggered by | A button | Typing a question |
| Purpose | Fixed 2-sentence debrief for non-technical readers | Open-ended questions and follow-ups |
| Where the fact sheet goes | `user` message (instructions in `system`) | Inside the `system` message |
| Conversation history | None: one request, one answer | Last 10 messages sent with each question |
| Response | Returned in one piece (`stream: false`) | Streamed word by word (`stream: true`) |
| Saved | To `<run file>.summary.txt`, reused next time | Only in the browser session |
| Shared rules | Same grounding rules, temperature 0.2, same fact sheet | Same |
