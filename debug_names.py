#!/usr/bin/env python3
"""Quick diagnostic — prints exact team names returned by the MLB standings API."""

import requests

BASE_URL = "https://statsapi.mlb.com/api/v1"
SEASON = 2026

url = f"{BASE_URL}/standings?leagueId=103,104&season={SEASON}&standingsTypes=regularSeason"
resp = requests.get(url, timeout=10)
data = resp.json()

print("Exact team names from MLB API:\n")
for record in data.get('records', []):
    for team_record in record.get('teamRecords', []):
        name = team_record['team']['name']
        w = team_record['wins']
        l = team_record['losses']
        print(f"  '{name}'  ({w}-{l})")
