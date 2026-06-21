"""
Seed election RESULTS for all 16 Taraba LGAs in one run.

Outcome (by design):
  * APC leads the STATEWIDE total.
  * APC wins 10 LGAs, PDP wins the remaining 6.
  * SDP and ADC trail in every LGA.

How it works:
  Each LGA's party totals (below) are spread across ALL of that LGA's polling
  units as real ElectionResult rows, so every ward and polling unit carries
  plausible numbers — not just the first ward. The split is randomised (fixed
  seed, reproducible) but always sums EXACTLY to the LGA target, so per-LGA
  winners and statewide totals are guaranteed.

  This is a clean reseed: it first deletes all existing ElectionResult and
  WardResult rows (including the earlier first-ward-only seed), then rebuilds.

Run it from the backend project root:
    python seed_results.py
"""

import os
import random
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from election.models import (
    LocalGovernmentArea, Ward, PollingUnit,
    PoliticalParty, ElectionResult, WardResult,
)

RNG = random.Random(42)  # fixed seed -> reproducible distribution


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


def split_total(total, n):
    """Split `total` into `n` non-negative ints (randomised) that sum to total."""
    if n <= 0:
        return []
    if n == 1:
        return [total]
    weights = [RNG.random() * 0.6 + 0.7 for _ in range(n)]  # 0.7 .. 1.3
    s = sum(weights)
    raw = [total * w / s for w in weights]
    floored = [int(x) for x in raw]
    remainder = total - sum(floored)
    # hand out the remainder to the largest fractional parts
    order = sorted(range(n), key=lambda i: raw[i] - floored[i], reverse=True)
    for i in range(remainder):
        floored[order[i]] += 1
    return floored


@transaction.atomic
def run():
    parties = {p.abbreviation.upper(): p for p in PoliticalParty.objects.all()}
    missing = {a for d in LGA_RESULTS.values() for a in d} - set(parties)
    if missing:
        raise SystemExit(f"Missing parties in DB: {sorted(missing)}. Found: {sorted(parties)}")

    lgas = {norm(l.name): l for l in LocalGovernmentArea.objects.all()}

    # Clean slate (removes the old first-ward-only override seed too)
    wr = WardResult.objects.all().delete()
    er = ElectionResult.objects.all().delete()
    print(f"Cleared {er[0]} ElectionResult and {wr[0]} WardResult rows.\n")

    overall = {a: 0 for a in parties}
    summary = []
    new_rows = []

    for lga_name, votes in LGA_RESULTS.items():
        lga = lgas.get(norm(lga_name))
        if not lga:
            print(f"  ! LGA not found, skipping: {lga_name}")
            continue

        pus = list(PollingUnit.objects.filter(ward__lga=lga).order_by('id'))
        if not pus:
            print(f"  ! No polling units for {lga.name}, skipping")
            continue

        for abbr, party in parties.items():
            target = votes.get(abbr, 0)
            for pu, share in zip(pus, split_total(target, len(pus))):
                new_rows.append(ElectionResult(polling_unit=pu, party=party, votes=share))
            overall[abbr] += target

        winner = max(votes, key=votes.get)
        summary.append((lga.name, winner, votes, len(pus)))

    ElectionResult.objects.bulk_create(new_rows, batch_size=500)

    # ---- Report ----
    print("=== Per-LGA winners (votes spread across all PUs) ===")
    for name, winner, votes, n_pu in summary:
        line = "  ".join(f"{a}:{votes.get(a, 0):>6}" for a in ('APC', 'PDP', 'SDP', 'ADC'))
        print(f"  {name:<14} winner={winner:<4} PUs={n_pu:<3} {line}")

    print(f"\n=== Statewide totals ({len(new_rows)} polling-unit result rows) ===")
    for abbr in ('APC', 'PDP', 'SDP', 'ADC'):
        print(f"  {abbr}: {overall.get(abbr, 0):,}")
    leader = max(overall, key=overall.get)
    apc_wins = sum(1 for _, w, _, _ in summary if w == 'APC')
    pdp_wins = sum(1 for _, w, _, _ in summary if w == 'PDP')
    print(f"\n  Overall leader: {leader}")
    print(f"  LGAs won -> APC: {apc_wins}, PDP: {pdp_wins}")
    print("\nDone. Refresh the landing page / map to see results.")


if __name__ == '__main__':
    run()
