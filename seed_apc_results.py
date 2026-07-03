"""
Seed election RESULTS for the APC dataset only (dataset='apc').

Goals (different from the 'main' seed on purpose):
  * APC still LEADS the statewide total.
  * But APC's winning LGAs are SCATTERED across the map instead of forming one
    solid block of colour. We do this by sorting LGAs by their geographic
    centroid and interleaving winners, so APC-won and PDP-won LGAs alternate in
    space.
  * Vote counts are more random: each LGA's turnout and party shares are drawn
    at random (fixed seed -> reproducible) and spread across ALL of that LGA's
    polling units.

Safety:
  * Operates ONLY on dataset='apc'. It deletes existing apc ElectionResult /
    WardResult rows and rebuilds them. The 'main' (my-app) data is never touched.

Run from the backend project root:
    python seed_apc_results.py
"""

import os
import random
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from django.db.models import Sum
from election.models import (
    LocalGovernmentArea, PollingUnit,
    PoliticalParty, ElectionResult, WardResult,
)

DATASET = 'apc'
RNG = random.Random(2027)  # fixed seed -> reproducible

# Force PDP's statewide total to this exact figure (APC still leads overall and
# the per-LGA winner map is preserved exactly).
PDP_TARGET_TOTAL = 202_322


def norm(s):
    return ' '.join((s or '').lower().replace('-', ' ').split())


# LGA centroids (cx, cy) from apc/lib/taraba-map.ts — used only to order LGAs in
# space so we can scatter the winners.
CENTROIDS = {
    'ardo kola': (762.1, 301.7),
    'bali': (662.5, 540.4),
    'donga': (443.7, 719.9),
    'gashaka': (796.9, 766.2),
    'gassol': (514.9, 427.5),
    'ibi': (274.9, 439.7),
    'jalingo': (796.8, 257.5),
    'karim lamido': (604.2, 180.9),
    'kurmi': (543.1, 868.4),
    'lau': (827.9, 170.3),
    'sardauna': (753.6, 962.4),
    'takum': (313.0, 877.7),
    'ussa': (334.6, 893.2),
    'wukari': (234.8, 595.0),
    'yorro': (876.3, 271.1),
    'zing': (933.9, 271.0),
}


def split_total(total, n):
    """Split `total` into `n` non-negative ints (randomised) summing to total."""
    if n <= 0:
        return []
    if n == 1:
        return [total]
    weights = [RNG.random() * 0.8 + 0.6 for _ in range(n)]  # 0.6 .. 1.4 (wide)
    s = sum(weights)
    raw = [total * w / s for w in weights]
    floored = [int(x) for x in raw]
    remainder = total - sum(floored)
    order = sorted(range(n), key=lambda i: raw[i] - floored[i], reverse=True)
    for i in range(remainder):
        floored[order[i]] += 1
    return floored


def assign_winners(ordered_names):
    """Given LGA names sorted in geographic order, hand out winners so APC's
    wins are interleaved through space (never a solid block).

    APC takes every even slot plus one extra -> 9 of 16; PDP takes the rest.
    Because the list is spatially sorted, alternating winners disperses them.
    """
    winners = {}
    for idx, name in enumerate(ordered_names):
        winners[name] = 'APC' if idx % 2 == 0 else 'PDP'
    # flip one PDP slot near the middle to APC so APC wins 9 LGAs total,
    # keeping the statewide lead comfortable while staying scattered.
    odd_names = [n for i, n in enumerate(ordered_names) if i % 2 == 1]
    if odd_names:
        winners[odd_names[len(odd_names) // 2]] = 'APC'
    return winners


@transaction.atomic
def run():
    parties = {p.abbreviation.upper(): p for p in PoliticalParty.objects.all()}
    for needed in ('APC', 'PDP', 'SDP', 'ADC'):
        if needed not in parties:
            raise SystemExit(f"Party {needed} missing. Found: {sorted(parties)}")

    lgas = list(LocalGovernmentArea.objects.filter(dataset=DATASET))
    if not lgas:
        raise SystemExit(
            f"No LGAs in dataset '{DATASET}'. Run: python manage.py clone_dataset --target apc"
        )

    # Order LGAs by geographic position (north->south bands, west->east within)
    def sort_key(lga):
        cx, cy = CENTROIDS.get(norm(lga.name), (500.0, 500.0))
        return (round(cy / 120.0), cx)

    ordered = sorted(lgas, key=sort_key)
    ordered_names = [norm(l.name) for l in ordered]
    winners = assign_winners(ordered_names)

    # Clean slate — apc dataset ONLY
    wr = WardResult.objects.filter(dataset=DATASET).delete()
    er = ElectionResult.objects.filter(dataset=DATASET).delete()
    print(f"Cleared {er[0]} apc ElectionResult and {wr[0]} apc WardResult rows.\n")

    # ---- Pass 1: per-LGA APC / SDP / ADC totals (PDP filled in afterwards) ----
    per_lga = []  # list of dicts: {lga, winner, pus, apc, sdp, adc}
    for lga in ordered:
        key = norm(lga.name)
        winner = winners[key]

        pus = list(PollingUnit.objects.filter(ward__lga=lga, dataset=DATASET).order_by('id'))
        if not pus:
            print(f"  ! No polling units for {lga.name}, skipping")
            continue

        # Randomised turnout off registered voters (fallback if none recorded)
        reg = sum(pu.registered_voters for pu in pus) or len(pus) * 500
        cast = int(reg * RNG.uniform(0.35, 0.62))

        # Randomised vote shares; the winner is strictly on top of the runner-up
        w_share = RNG.uniform(0.40, 0.52)
        l_share = RNG.uniform(0.26, min(0.36, w_share - 0.05))
        sdp_share = RNG.uniform(0.03, 0.08)
        adc_share = RNG.uniform(0.02, 0.06)
        total_share = w_share + l_share + sdp_share + adc_share

        apc_share = w_share if winner == 'APC' else l_share
        per_lga.append({
            'lga': lga,
            'winner': winner,
            'pus': pus,
            'apc': int(cast * apc_share / total_share),
            'sdp': int(cast * sdp_share / total_share),
            'adc': int(cast * adc_share / total_share),
        })

    # ---- Allocate PDP so its statewide total is EXACTLY PDP_TARGET_TOTAL ----
    # PDP-won LGAs must stay above their APC number; APC-won LGAs must stay below.
    pdp = {}
    for r in per_lga:
        if r['winner'] == 'PDP':
            lead = max(1, round(r['apc'] * RNG.uniform(0.06, 0.14)))
            pdp[r['lga'].id] = r['apc'] + lead

    used = sum(pdp.values())
    apc_won = [r for r in per_lga if r['winner'] == 'APC']
    remaining = PDP_TARGET_TOTAL - used
    if remaining < len(apc_won):
        raise SystemExit(
            f"PDP target {PDP_TARGET_TOTAL:,} too low to keep the winner map "
            f"(PDP already needs {used:,} to win its LGAs)."
        )

    weight_total = sum(r['apc'] for r in apc_won) or 1
    for r in apc_won:
        share = int(remaining * r['apc'] / weight_total)
        pdp[r['lga'].id] = min(r['apc'] - 1, max(1, share))  # strictly below APC

    # Fix rounding drift so the grand total lands exactly on PDP_TARGET_TOTAL
    drift = PDP_TARGET_TOTAL - sum(pdp.values())
    step = 1 if drift > 0 else -1
    idx = 0
    while drift != 0 and apc_won:
        r = apc_won[idx % len(apc_won)]
        cur = pdp[r['lga'].id]
        if 1 <= cur + step <= r['apc'] - 1:
            pdp[r['lga'].id] = cur + step
            drift -= step
        idx += 1
        if idx > len(apc_won) * 100000:
            raise SystemExit("Could not reconcile PDP total — check constraints.")

    # ---- Pass 2: spread each party's LGA total across its polling units ----
    overall = {a: 0 for a in parties}
    summary = []
    new_rows = []
    for r in per_lga:
        lga, pus = r['lga'], r['pus']
        votes = {'APC': r['apc'], 'PDP': pdp[lga.id], 'SDP': r['sdp'], 'ADC': r['adc']}
        for abbr, target in votes.items():
            party = parties[abbr]
            for pu, share in zip(pus, split_total(target, len(pus))):
                new_rows.append(ElectionResult(
                    polling_unit=pu, party=party, votes=share, dataset=DATASET,
                ))
            overall[abbr] += target
        summary.append((lga.name, r['winner'], votes, len(pus)))

    ElectionResult.objects.bulk_create(new_rows, batch_size=500)

    # ---- Report ----
    print("=== Per-LGA winners (apc dataset, votes spread across all PUs) ===")
    for name, winner, votes, n_pu in summary:
        line = "  ".join(f"{a}:{votes.get(a, 0):>6}" for a in ('APC', 'PDP', 'SDP', 'ADC'))
        print(f"  {name:<14} winner={winner:<4} PUs={n_pu:<3} {line}")

    print(f"\n=== Statewide totals ({len(new_rows)} result rows) ===")
    for abbr in ('APC', 'PDP', 'SDP', 'ADC'):
        print(f"  {abbr}: {overall.get(abbr, 0):,}")
    leader = max(overall, key=overall.get)
    apc_wins = sum(1 for _, w, _, _ in summary if w == 'APC')
    pdp_wins = sum(1 for _, w, _, _ in summary if w == 'PDP')
    print(f"\n  Overall leader: {leader}")
    print(f"  LGAs won -> APC: {apc_wins}, PDP: {pdp_wins}")

    if leader != 'APC':
        raise SystemExit("APC did not lead statewide — aborting (transaction rolled back).")

    print("\nDone. Refresh the apc landing page / map to see the scattered result.")


if __name__ == '__main__':
    run()
