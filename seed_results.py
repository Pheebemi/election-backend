"""
Seed election RESULTS for all 16 Taraba LGAs in one run.

Outcome (by design):
  * APC leads the STATEWIDE total.
  * APC wins 10 LGAs, PDP wins the remaining 6.
  * SDP and ADC trail in every LGA.

How it works (non-destructive to polling-unit data):
  For each LGA we put that LGA's full party totals as a WARD OVERRIDE on the
  LGA's first ward, and set 0 overrides on all the LGA's other wards. The
  chart_data endpoint uses ward overrides ahead of polling-unit sums, so the
  per-LGA totals become exactly the numbers below regardless of any existing
  polling-unit entries. No ElectionResult rows are deleted.

Run it from the backend project root:
    python seed_results.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from election.models import LocalGovernmentArea, Ward, PoliticalParty, WardResult


def norm(s):
    return ' '.join((s or '').lower().replace('-', ' ').split())


# Per-LGA totals: {LGA: {party_abbr: votes}}
# First 10 -> APC wins.  Last 6 -> PDP wins.
LGA_RESULTS = {
    # ---- APC-won LGAs (10) ----
    'Jalingo':      {'APC': 18200, 'PDP': 12400, 'SDP': 2600, 'ADC': 1800},
    'Ardo-kola':    {'APC': 14100, 'PDP': 9800,  'SDP': 1900, 'ADC': 1300},
    'Bali':         {'APC': 15600, 'PDP': 11200, 'SDP': 2300, 'ADC': 1600},
    'Gassol':       {'APC': 16800, 'PDP': 12900, 'SDP': 2700, 'ADC': 1500},
    'Ibi':          {'APC': 12400, 'PDP': 8700,  'SDP': 1600, 'ADC': 1100},
    'Lau':          {'APC': 11900, 'PDP': 8200,  'SDP': 1500, 'ADC': 1000},
    'Yorro':        {'APC': 10800, 'PDP': 7600,  'SDP': 1400, 'ADC': 900},
    'Zing':         {'APC': 13200, 'PDP': 9100,  'SDP': 1800, 'ADC': 1200},
    'Karim Lamido': {'APC': 15100, 'PDP': 11800, 'SDP': 2400, 'ADC': 1700},
    'Sardauna':     {'APC': 17400, 'PDP': 13100, 'SDP': 2900, 'ADC': 2000},
    # ---- PDP-won LGAs (6) ----
    'Donga':        {'PDP': 14600, 'APC': 10300, 'SDP': 2100, 'ADC': 1500},
    'Gashaka':      {'PDP': 9800,  'APC': 6900,  'SDP': 1300, 'ADC': 900},
    'Kurmi':        {'PDP': 10400, 'APC': 7400,  'SDP': 1500, 'ADC': 1000},
    'Takum':        {'PDP': 13800, 'APC': 10100, 'SDP': 2200, 'ADC': 1600},
    'Ussa':         {'PDP': 11200, 'APC': 8300,  'SDP': 1700, 'ADC': 1100},
    'Wukari':       {'PDP': 16900, 'APC': 12700, 'SDP': 3000, 'ADC': 2100},
}


def run():
    # Parties keyed by abbreviation (case-insensitive)
    parties = {p.abbreviation.upper(): p for p in PoliticalParty.objects.all()}
    missing_parties = {a for d in LGA_RESULTS.values() for a in d} - set(parties)
    if missing_parties:
        raise SystemExit(f"Missing parties in DB: {sorted(missing_parties)}. "
                         f"Found: {sorted(parties)}")

    # LGAs keyed by normalized name
    lgas = {norm(l.name): l for l in LocalGovernmentArea.objects.all()}

    overall = {a: 0 for a in parties}
    summary = []
    n_overrides = 0

    for lga_name, votes in LGA_RESULTS.items():
        lga = lgas.get(norm(lga_name))
        if not lga:
            print(f"  ! LGA not found, skipping: {lga_name}")
            continue

        wards = list(Ward.objects.filter(lga=lga).order_by('id'))
        if not wards:
            print(f"  ! No wards for {lga.name}, skipping")
            continue

        first, rest = wards[0], wards[1:]

        # Full LGA totals on the first ward
        for abbr, party in parties.items():
            v = votes.get(abbr, 0)
            WardResult.objects.update_or_create(
                ward=first, party=party, defaults={'votes': v, 'entered_by': None}
            )
            overall[abbr] += v
            n_overrides += 1

        # Zero overrides on every other ward of this LGA (mask any stray data)
        for w in rest:
            for party in parties.values():
                WardResult.objects.update_or_create(
                    ward=w, party=party, defaults={'votes': 0, 'entered_by': None}
                )
                n_overrides += 1

        winner = max(votes, key=votes.get)
        summary.append((lga.name, winner, votes))

    # ---- Report ----
    print("\n=== Per-LGA winners ===")
    for name, winner, votes in summary:
        line = "  ".join(f"{a}:{votes.get(a, 0):>6}" for a in ('APC', 'PDP', 'SDP', 'ADC'))
        print(f"  {name:<14} winner={winner:<4}  {line}")

    print(f"\n=== Statewide totals ({n_overrides} ward-override rows written) ===")
    for abbr in ('APC', 'PDP', 'SDP', 'ADC'):
        print(f"  {abbr}: {overall.get(abbr, 0):,}")
    leader = max(overall, key=overall.get)
    apc_wins = sum(1 for _, w, _ in summary if w == 'APC')
    pdp_wins = sum(1 for _, w, _ in summary if w == 'PDP')
    print(f"\n  Overall leader: {leader}")
    print(f"  LGAs won -> APC: {apc_wins}, PDP: {pdp_wins}")
    print("\nDone. Refresh the landing page / map to see results.")


if __name__ == '__main__':
    run()
