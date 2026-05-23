#!/usr/bin/env python3
"""
MLB Model - Data Combiner
Merges bullpen.json and expectations.json into a single combined.json
that the dashboard reads from. Run this after both pillar scripts complete.
"""

import json
from datetime import datetime

# Maps short names (from standings API) to full names (from teams API)
SHORT_TO_FULL = {
    "D-backs":    "Arizona Diamondbacks",
    "Braves":     "Atlanta Braves",
    "Orioles":    "Baltimore Orioles",
    "Red Sox":    "Boston Red Sox",
    "Cubs":       "Chicago Cubs",
    "White Sox":  "Chicago White Sox",
    "Reds":       "Cincinnati Reds",
    "Guardians":  "Cleveland Guardians",
    "Rockies":    "Colorado Rockies",
    "Tigers":     "Detroit Tigers",
    "Astros":     "Houston Astros",
    "Royals":     "Kansas City Royals",
    "Angels":     "Los Angeles Angels",
    "Dodgers":    "Los Angeles Dodgers",
    "Marlins":    "Miami Marlins",
    "Brewers":    "Milwaukee Brewers",
    "Twins":      "Minnesota Twins",
    "Mets":       "New York Mets",
    "Yankees":    "New York Yankees",
    "Athletics":  "Oakland Athletics",
    "Phillies":   "Philadelphia Phillies",
    "Pirates":    "Pittsburgh Pirates",
    "Padres":     "San Diego Padres",
    "Giants":     "San Francisco Giants",
    "Mariners":   "Seattle Mariners",
    "Cardinals":  "St. Louis Cardinals",
    "Rays":       "Tampa Bay Rays",
    "Rangers":    "Texas Rangers",
    "Blue Jays":  "Toronto Blue Jays",
    "Nationals":  "Washington Nationals"
}


def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)


def run():
    print(f"\n{'='*50}")
    print(f"  MLB Model Combiner  |  {datetime.today().strftime('%Y-%m-%d')}")
    print(f"{'='*50}\n")

    print("Loading pillar data...")
    bullpen_data = load_json('data/bullpen.json')
    expectations_data = load_json('data/expectations.json')

    # Build bullpen lookup by full name
    bullpen_by_full_name = {}
    for b_id, b_team in bullpen_data['teams'].items():
        bullpen_by_full_name[b_team['name']] = b_team['bullpen']

    combined = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'as_of_date': datetime.today().strftime('%Y-%m-%d'),
        'teams': []
    }

    for team_id, exp_team in expectations_data['teams'].items():
        short_name = exp_team['name']
        expectation = exp_team['expectation']

        # Resolve full name and look up bullpen
        full_name = SHORT_TO_FULL.get(short_name, short_name)
        bullpen = bullpen_by_full_name.get(full_name)

        if bullpen is None:
            print(f"  ⚠️  No bullpen match for '{short_name}' → '{full_name}'")
            bullpen = {'score': 1.0, 'label': 'Full', 'emoji': '🟢', 'relievers': []}

        combined['teams'].append({
            'id': team_id,
            'name': short_name,
            'full_name': full_name,
            'bullpen': {
                'score': bullpen['score'],
                'label': bullpen['label'],
                'emoji': bullpen['emoji'],
                'relievers': bullpen.get('relievers', [])
            },
            'expectation': {
                'preseason_win_total': expectation['preseason_win_total'],
                'actual_wins': expectation['actual_wins'],
                'actual_losses': expectation['actual_losses'],
                'games_played': expectation['games_played'],
                'win_pct': expectation['win_pct'],
                'expected_wins': expectation['expected_wins'],
                'delta': expectation['delta'],
                'projected_wins': expectation['projected_wins'],
                'label': expectation['label'],
                'description': expectation['description']
            }
        })

    # Sort by expectation delta descending
    combined['teams'].sort(key=lambda x: x['expectation']['delta'], reverse=True)

    with open('data/combined.json', 'w') as f:
        json.dump(combined, f, indent=2)

    print(f"✅ Combined {len(combined['teams'])} teams into data/combined.json")
    print(f"\nQuick snapshot:")
    print(f"{'Team':<25} {'Bullpen':<12} {'Delta':<8} {'Status'}")
    print("-" * 65)
    for team in combined['teams']:
        b = team['bullpen']
        e = team['expectation']
        print(f"{team['name']:<25} {b['emoji']} {b['label']:<10} {e['delta']:+.1f}     {e['label']}")

    return combined


if __name__ == '__main__':
    run()
