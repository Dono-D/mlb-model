#!/usr/bin/env python3
"""
MLB Performance vs. Expectation Tracker
Compares each team's current record against their preseason win total pace.
Outputs a delta score and trend label for each team.
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
    Returns list of team records: {name, wins, losses, games_played, team_id}
    """
    url = f"{BASE_URL}/standings?leagueId=103,104&season={SEASON}&standingsTypes=regularSeason"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()

    teams = []
    for record in resp.json().get('records', []):
        for team_record in record.get('teamRecords', []):
            teams.append({
                'team_id': team_record['team']['id'],
                'name': team_record['team']['name'],
                'wins': team_record['wins'],
                'losses': team_record['losses'],
                'games_played': team_record['gamesPlayed'],
                'win_pct': float(team_record.get('winningPercentage', 0))
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
    """
    Compare a team's actual record to their preseason win total pace.

    Expected wins = (win_total / 162) * games_played
    Delta = actual_wins - expected_wins

    Positive delta = outperforming
    Negative delta = underperforming
    """
    name = team['name']
    win_total = win_totals.get(name)

    if win_total is None:
        return None

    games_played = team['games_played']
    if games_played == 0:
        return None

    expected_wins = (win_total / TOTAL_GAMES) * games_played
    delta = team['wins'] - expected_wins

    # Pace: projected wins over full season at current rate
    projected_wins = (team['wins'] / games_played) * TOTAL_GAMES if games_played > 0 else win_total

    # Label
    if delta >= 5:
        label = 'Hot 🔥'
        description = 'Significantly outperforming expectations'
    elif delta >= 2:
        label = 'Ahead 📈'
        description = 'Slightly outperforming expectations'
    elif delta >= -2:
        label = 'On Track ➡️'
        description = 'Performing in line with expectations'
    elif delta >= -5:
        label = 'Behind 📉'
        description = 'Slightly underperforming expectations'
    else:
        label = 'Cold ❄️'
        description = 'Significantly underperforming expectations'

    return {
        'preseason_win_total': win_total,
        'games_played': games_played,
        'actual_wins': team['wins'],
        'actual_losses': team['losses'],
        'win_pct': team['win_pct'],
        'expected_wins': round(expected_wins, 1),
        'delta': round(delta, 1),
        'projected_wins': round(projected_wins, 1),
        'label': label,
        'description': description
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
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'as_of_date': datetime.today().strftime('%Y-%m-%d'),
        'win_totals_last_updated': last_updated,
        'teams': {}
    }

    # Sort by delta for easy reading
    results = []
    for team in standings:
        expectation = calculate_expectation(team, win_totals)
        if expectation:
            results.append({
                'team_id': team['team_id'],
                'name': team['name'],
                'expectation': expectation
            })

    results.sort(key=lambda x: x['expectation']['delta'], reverse=True)

    print(f"{'Team':<30} {'W-L':<8} {'Expected W':<12} {'Delta':<8} {'Label'}")
    print("-" * 75)

    for r in results:
        e = r['expectation']
        wl = f"{e['actual_wins']}-{e['actual_losses']}"
        print(f"{r['name']:<30} {wl:<8} {e['expected_wins']:<12} {e['delta']:+.1f}    {e['label']}")

        output['teams'][str(r['team_id'])] = {
            'name': r['name'],
            'expectation': r['expectation']
        }

    with open('data/expectations.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Done. Output saved to data/expectations.json")
    return output


if __name__ == '__main__':
    run()
