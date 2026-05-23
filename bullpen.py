#!/usr/bin/env python3
"""
MLB Bullpen Tracker
Fetches recent pitcher usage and calculates bullpen availability (gas tank) for all 30 teams.
Data source: MLB Stats API (free, no key required)
"""

import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict

BASE_URL = "https://statsapi.mlb.com/api/v1"


# ─────────────────────────────────────────────
# UTILITY
# ─────────────────────────────────────────────

def parse_ip(ip_str):
    """
    Convert MLB innings pitched string to decimal innings.
    MLB uses .1 = 1 out (1/3 inning), .2 = 2 outs (2/3 inning)
    e.g. "2.1" → 2.333, "1.2" → 1.667
    """
    if not ip_str:
        return 0.0
    parts = str(ip_str).split('.')
    full_innings = int(parts[0])
    outs = int(parts[1]) if len(parts) > 1 else 0
    return full_innings + (outs / 3)


# ─────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────

def get_all_teams():
    """Fetch all 30 MLB teams. Returns dict of {team_id: team_name}."""
    url = f"{BASE_URL}/teams?sportId=1&activeStatus=Y"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    teams = {t['id']: t['name'] for t in resp.json()['teams']}
    return teams


def get_recent_games(team_id, days=5):
    """
    Get completed regular season game IDs for a team over the last N days.
    Returns list of {gamePk, date} dicts.
    """
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)

    url = (
        f"{BASE_URL}/schedule?sportId=1"
        f"&startDate={start_date.strftime('%Y-%m-%d')}"
        f"&endDate={end_date.strftime('%Y-%m-%d')}"
        f"&teamId={team_id}"
        f"&gameType=R"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()

    games = []
    for date_entry in resp.json().get('dates', []):
        for game in date_entry.get('games', []):
            if game['status']['abstractGameState'] == 'Final':
                games.append({
                    'gamePk': game['gamePk'],
                    'date': date_entry['date']
                })
    return games


def get_boxscore(game_pk):
    """Fetch full boxscore for a game."""
    url = f"{BASE_URL}/game/{game_pk}/boxscore"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def extract_relief_pitchers(boxscore, team_id):
    """
    Extract relief pitcher appearances from a boxscore for a specific team.
    First pitcher in the list = starter, rest = relievers.
    Returns list of {id, name, ip} dicts.
    """
    home_id = boxscore['teams']['home']['team']['id']
    side = 'home' if team_id == home_id else 'away'

    pitcher_ids = boxscore['teams'][side].get('pitchers', [])
    all_players = boxscore['teams'][side].get('players', {})

    relievers = []
    for i, pitcher_id in enumerate(pitcher_ids):
        if i == 0:
            continue  # Skip starter

        player_key = f"ID{pitcher_id}"
        player_data = all_players.get(player_key, {})
        stats = player_data.get('stats', {}).get('pitching', {})
        ip_str = stats.get('inningsPitched', '0')
        name = player_data.get('person', {}).get('fullName', 'Unknown')

        relievers.append({
            'id': pitcher_id,
            'name': name,
            'ip': parse_ip(ip_str)
        })

    return relievers


# ─────────────────────────────────────────────
# AVAILABILITY CALCULATION
# ─────────────────────────────────────────────

def calculate_pitcher_availability(appearances):
    """
    Calculate availability score (0.0 → 1.0) for a single reliever.

    Deduction logic:
    - Pitched today       → nearly unavailable (-0.9)
    - Pitched yesterday   → heavy deduction, scaled by IP
    - Pitched 2 days ago  → moderate deduction, scaled by IP
    - 3+ days ago         → minimal impact
    - High cumulative IP  → additional fatigue penalty
    """
    today = datetime.today().date()
    score = 1.0
    total_ip = 0.0

    for app in appearances:
        app_date = datetime.strptime(app['date'], '%Y-%m-%d').date()
        days_ago = (today - app_date).days
        ip = app['ip']
        total_ip += ip

        if days_ago == 0:
            score -= 0.90
        elif days_ago == 1:
            score -= 0.55 if ip >= 2.0 else 0.35
        elif days_ago == 2:
            score -= 0.20 if ip >= 2.0 else 0.10

    # Cumulative workload penalty
    if total_ip >= 4.0:
        score -= 0.20
    elif total_ip >= 2.5:
        score -= 0.10

    return round(max(0.0, min(1.0, score)), 3)


def calculate_team_bullpen(team_id, games):
    """
    Aggregate reliever availability into a team-level gas tank score.
    Uses top 7 relievers by recent workload (approximates actual pen depth).

    Returns:
        score  → 0.0 to 1.0
        label  → Full / Half / Low / Empty
        emoji  → color indicator
        detail → per-reliever breakdown
    """
    today = datetime.today().date()
    reliever_log = defaultdict(list)  # {pitcher_id: [{date, name, ip}]}

    for game in games:
        try:
            boxscore = get_boxscore(game['gamePk'])
            relievers = extract_relief_pitchers(boxscore, team_id)
            for r in relievers:
                reliever_log[r['id']].append({
                    'name': r['name'],
                    'date': game['date'],
                    'ip': r['ip']
                })
        except Exception as e:
            print(f"  Warning: could not process game {game['gamePk']}: {e}")
            continue

    if not reliever_log:
        return _gas_tank(1.0, [])

    # Build per-reliever summary
    summaries = []
    for pitcher_id, apps in reliever_log.items():
        name = apps[0]['name']
        avail = calculate_pitcher_availability(apps)
        last_date = max(apps, key=lambda x: x['date'])['date']
        days_rest = (today - datetime.strptime(last_date, '%Y-%m-%d').date()).days
        total_ip = round(sum(a['ip'] for a in apps), 2)

        summaries.append({
            'name': name,
            'availability': avail,
            'days_rest': days_rest,
            'recent_ip': total_ip
        })

    # Sort by workload (most-used relievers are the meaningful pen arms)
    summaries.sort(key=lambda x: x['recent_ip'], reverse=True)
    top_arms = summaries[:7]

    team_score = sum(r['availability'] for r in top_arms) / len(top_arms)
    return _gas_tank(round(team_score, 3), sorted(top_arms, key=lambda x: x['availability']))


def _gas_tank(score, detail):
    """Map a 0–1 score to a human-readable gas tank label."""
    if score >= 0.75:
        label, emoji = 'Full', '🟢'
    elif score >= 0.50:
        label, emoji = 'Half', '🟡'
    elif score >= 0.25:
        label, emoji = 'Low', '🟠'
    else:
        label, emoji = 'Empty', '🔴'

    return {'score': score, 'label': label, 'emoji': emoji, 'relievers': detail}


# ─────────────────────────────────────────────
# MAIN RUNNER
# ─────────────────────────────────────────────

def run():
    print(f"\n{'='*50}")
    print(f"  MLB Bullpen Tracker  |  {datetime.today().strftime('%Y-%m-%d')}")
    print(f"{'='*50}\n")

    print("Fetching teams...")
    teams = get_all_teams()
    print(f"Found {len(teams)} teams.\n")

    output = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'as_of_date': datetime.today().strftime('%Y-%m-%d'),
        'teams': {}
    }

    for team_id, team_name in sorted(teams.items(), key=lambda x: x[1]):
        print(f"Processing {team_name}...")
        try:
            games = get_recent_games(team_id, days=5)
            bullpen = calculate_team_bullpen(team_id, games)
            print(f"  → Bullpen: {bullpen['emoji']} {bullpen['label']} ({bullpen['score']})")
        except Exception as e:
            print(f"  → Error: {e}")
            bullpen = _gas_tank(1.0, [])

        output['teams'][str(team_id)] = {
            'name': team_name,
            'bullpen': bullpen
        }

    with open('data/bullpen.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Done. Output saved to data/bullpen.json")
    return output


if __name__ == '__main__':
    run()
