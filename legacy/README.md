# Legacy (retired) files

These are the first versions of the project. They are kept for reference and for comparison with
the current code, but **nothing in the live pipeline uses them**.

| File | What it was | Replaced by |
|---|---|---|
| `dashboard.py` | First Streamlit dashboard. Downloaded every telemetry file before drawing anything | `dashboard_v2.py` |
| `sync_outputs.py` | S3 uploader that re-uploaded every file every 10 seconds | `sync_outputs_v2.py` |
| `race_engineer.py` | Terminal listener that printed an AI debrief for each new run | The Automated Engineer Brief in the dashboard |
| `pit_radio.py` | Terminal chat with the AI engineer about the latest run | The Pit Radio Channel in the dashboard |
| `telemetry_parser.py` | Loaded parquet files and computed summary stats (used only by the two scripts above) | `telemetry_context.py` |
| `read_logs.py` | Printed the telemetry column names | The column guide in [`examples/README.md`](../examples/README.md) |

The terminal tools still use the original, thinner summary and do not have the grounding fixes
described in [`docs/preventing_hallucinations.md`](../docs/preventing_hallucinations.md). To try one,
run it from the repository root so it finds `outputs/`:

```powershell
python legacy/pit_radio.py
```
