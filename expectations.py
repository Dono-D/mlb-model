#!/usr/bin/env python3
"""
MLB Performance vs. Expectation Tracker
Compares each team's current record against their preseason win total pace.
Outputs a delta score, trend label, streak, and last 10 record for each team.
"""

import requests
import json
from datetime import datetime

BASE_URL = "https://statsapi.mlb.com/api/v1"
SEASON = 2026
TOTAL_GAMES = 162


# ─────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────

def get_standings():
    """
    Fetch current MLB standings for both leagues.
    Returns list of team records including streak and last 10.
    """
    url = f"{BASE_URL}/standings?leagueId=103,104&season={SEASON}&standingsTypes=regularSeason"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()

    teams = []
    for record in resp.json().get('records', []):
        for team_record in record.get('teamRecords', []):

            # Streak
            streak_info = team_record.get('streak', {})
            streak_type = streak_info.get('streakType', '')
            streak_num  = streak_info.get('streakNumber', 0)
            if streak_type == 'wins':
                streak = f"W{streak_num}"
            elif streak_type == 'losses':
                streak = f"L{streak_num}"
            else:
                streak = '-'

            # Last 10
            records = team_record.get('records', {})
            split_records = records.get('splitRecords', [])
            last10_wins = 0
            last10_losses = 0
            for split in split_records:
                if split.get('type') == 'lastTen':
                    last10_wins   = split.get('wins', 0)
                    last10_losses = split.get('losses', 0)
                    break

            teams.append({
                'team_id':     team_record['team']['id'],
                'name':        team_record['team']['name'],
                'wins':        team_record['wins'],
                'losses':      team_record['losses'],
                'games_played': team_record['gamesPlayed'],
                'win_pct':     float(team_record.get('winningPercentage', 0)),
                'streak':      streak,
                'last10_wins':   last10_wins,
                'last10_losses': last10_losses,
            })
    return teams


def load_win_totals():
    """Load preseason win totals from config file."""
    with open('win_totals.json', 'r') as f:
        data = json.load(f)
    return data['win_totals'], data.get('last_updated', 'unknown')


# ─────────────────────────────────────────────
# EXPECTATION CALCULATION
# ─────────────────────────────────────────────

def calculate_expectation(team, win_totals):
    name      = team['name']
    win_total = win_totals.get(name)

    if win_total is None:
        return None

    games_played = team['games_played']
    if games_played == 0:
        return None

    expected_wins  = (win_total / TOTAL_GAMES) * games_played
    delta          = team['wins'] - expected_wins
    projected_wins = (team['wins'] / games_played) * TOTAL_GAMES

    if delta >= 5:
        label       = 'Hot 🔥'
        description = 'Significantly outperforming expectations'
    elif delta >= 2:
        label       = 'Ahead 📈'
        description = 'Slightly outperforming expectations'
    elif delta >= -2:
        label       = 'On Track ➡️'
        description = 'Performing in line with expectations'
    elif delta >= -5:
        label       = 'Behind 📉'
        description = 'Slightly underperforming expectations'
    else:
        label       = 'Cold ❄️'
        description = 'Significantly underperforming expectations'

    return {
        'preseason_win_total': win_total,
        'games_played':        games_played,
        'actual_wins':         team['wins'],
        'actual_losses':       team['losses'],
        'win_pct':             team['win_pct'],
        'expected_wins':       round(expected_wins, 1),
        'delta':               round(delta, 1),
        'projected_wins':      round(projected_wins, 1),
        'label':               label,
        'description':         description,
        'streak':              team['streak'],
        'last10_wins':         team['last10_wins'],
        'last10_losses':       team['last10_losses'],
    }


# ─────────────────────────────────────────────
# MAIN RUNNER
# ─────────────────────────────────────────────

def run():
    print(f"\n{'='*50}")
    print(f"  MLB Expectations Tracker  |  {datetime.today().strftime('%Y-%m-%d')}")
    print(f"{'='*50}\n")

    print("Loading preseason win totals...")
    win_totals, last_updated = load_win_totals()
    print(f"Win totals last updated: {last_updated}\n")

    print("Fetching current standings...")
    standings = get_standings()
    print(f"Found {len(standings)} teams.\n")

    output = {
        'generated_at':           datetime.utcnow().isoformat() + 'Z',
        'as_of_date':             datetime.today().strftime('%Y-%m-%d'),
        'win_totals_last_updated': last_updated,
        'teams': {}
    }

    results = []
    for team in standings:
        expectation = calculate_expectation(team, win_totals)
        if expectation:
            results.append({
                'team_id':    team['team_id'],
                'name':       team['name'],
                'expectation': expectation
            })

    results.sort(key=lambda x: x['expectation']['delta'], reverse=True)

    print(f"{'Team':<30} {'W-L':<8} {'L10':<8} {'Streak':<8} {'Delta':<8} {'Label'}")
    print("-" * 80)

    for r in results:
        e  = r['expectation']
        wl = f"{e['actual_wins']}-{e['actual_losses']}"
        l10 = f"{e['last10_wins']}-{e['last10_losses']}"
        print(f"{r['name']:<30} {wl:<8} {l10:<8} {e['streak']:<8} {e['delta']:+.1f}    {e['label']}")

        output['teams'][str(r['team_id'])] = {
            'name':        r['name'],
            'expectation': r['expectation']
        }

    with open('data/expectations.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Done. Output saved to data/expectations.json")
    return output


if __name__ == '__main__':
    run()
