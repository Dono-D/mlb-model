# MLB Bullpen Tracker — Setup Guide

## Prerequisites
Make sure you have Python 3.8+ installed. Open a terminal (Command Prompt or PowerShell on Windows).

## Step 1 — Install dependencies
```
pip install requests
```

## Step 2 — Create the project folder
```
mkdir mlb-model
cd mlb-model
mkdir data
```

## Step 3 — Add the script
Copy bullpen.py into your mlb-model folder.

## Step 4 — Run it
```
python bullpen.py
```

You should see output like:
```
==================================================
  MLB Bullpen Tracker  |  2026-05-23
==================================================

Fetching teams...
Found 30 teams.

Processing Arizona Diamondbacks...
  → Bullpen: 🟢 Full (0.812)
Processing Atlanta Braves...
  → Bullpen: 🟡 Half (0.541)
...

✅ Done. Output saved to data/bullpen.json
```

## Step 5 — Check output
Open data/bullpen.json to see all 30 teams with their bullpen scores and per-reliever breakdowns.

## Notes
- Script pulls last 5 days of completed regular season games
- Gas tank: 🟢 Full (≥0.75) | 🟡 Half (≥0.50) | 🟠 Low (≥0.25) | 🔴 Empty (<0.25)
- Runtime: ~3-5 minutes (making ~150+ API calls across 30 teams)
