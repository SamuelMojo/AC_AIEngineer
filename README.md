# AC Neural Net – Telemetry Pipeline

A live telemetry and race-engineering pipeline built around reinforcement-learning agents
training in Assetto Corsa.

The RL environment and the SAC/DisCor training code are **not** part of this repository.
They come from [assetto_corsa_gym](https://github.com/dasGringuen/assetto_corsa_gym)
(MIT, © 2024 Adrian Remonda), which is included as a git submodule in
`external/assetto_corsa_gym`. This repo contains the pipeline built around it.

## What's in this repo

| File | Purpose |
|---|---|
| `run_pipeline.ps1` | One-command launcher: starts Ollama and the EC2 instance, starts the S3 sync watcher, then runs training |
| `sync_outputs_v2.py` | Uploads new/changed lap telemetry (`outputs/**/laps/*.parquet`) to S3 |
| `dashboard_v2.py` | Streamlit dashboard: live and historical runs, reward progression, session scoping, pit-radio chat |
| `telemetry_parser.py` | Loads lap parquet files and summarises them for the AI engineer |
| `race_engineer.py`, `pit_radio.py` | Local LLM (Ollama) race engineer that comments on lap telemetry |
| `read_logs.py` | Quick inspection of telemetry logs |
| `config.yml` | Training config (adapted from assetto_corsa_gym – see `THIRD_PARTY_NOTICES.md`) |
| `.github/workflows/deploy.yml` | Post-deploy smoke test for the hosted dashboard |
| `dashboard.py`, `sync_outputs.py` | Earlier versions, kept for reference |

## Setup

```powershell
git clone --recurse-submodules https://github.com/SamuelMojo/AC_nueral_net.git
cd AC_nueral_net
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Then follow [assetto_corsa_gym's install guide](https://github.com/dasGringuen/assetto_corsa_gym/blob/main/INSTALL.md)
to install the Assetto Corsa plugin and vJoy.

## Running

```powershell
.\run_pipeline.ps1
```

Training runs from the submodule but uses this repo's `config.yml`, and writes to `outputs/`
in the repo root, which is where the sync watcher and dashboard look.

## Credits

- [assetto_corsa_gym](https://github.com/dasGringuen/assetto_corsa_gym) – Adrian Remonda et al., MIT
- [discor.pytorch](https://github.com/toshikwa/discor.pytorch) – SAC/DisCor implementation used by assetto_corsa_gym, MIT
