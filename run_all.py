#!/usr/bin/env python3
"""
MLB Model - Master Runner
Runs all scripts in sequence: bullpen → expectations → combine
This is the only script you need to run manually or via automation.
"""

import subprocess
import sys
from datetime import datetime

PYTHON = sys.executable
SCRIPTS = [
    ('bullpen.py',      'Pillar 1 — Bullpen Tracker'),
    ('expectations.py', 'Pillar 2 — Expectations Tracker'),
    ('combine.py',      'Combiner — Merging outputs'),
]

print(f"\n{'='*50}")
print(f"  MLB Model — Full Refresh")
print(f"  {datetime.today().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*50}")

for script, label in SCRIPTS:
    print(f"\n▶ Running {label}...")
    result = subprocess.run([PYTHON, script], capture_output=False)
    if result.returncode != 0:
        print(f"\n❌ {script} failed. Stopping.")
        sys.exit(1)

print(f"\n{'='*50}")
print(f"  ✅ All scripts complete. data/combined.json is ready.")
print(f"{'='*50}\n")
