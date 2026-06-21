"""
Import the FULL modern Taraba polling-unit structure (post-2021 expansion).

Source data: taraba_pus.json (bundled in this repo, compiled from the public
INEC dataset at github.com/sadiqsalau/inec-ng-data -> state 34 / Taraba).
  16 LGAs, 168 wards, 3,597 polling units.

WIPE-AND-REBUILD:
  This DELETES all existing Ward and PollingUnit rows, then rebuilds them from
  the JSON. Deleting wards/PUs cascades to ElectionResult and WardResult, so
  ALL RESULTS ARE CLEARED TOO. LGAs and Parties are kept (LGAs are matched by
  name; missing ones are created).

  After running this, re-run `python seed_results.py` to repopulate vote totals.

Run from the backend project root:
    python import_taraba_pus.py
"""

import os
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from election.models import (
    LocalGovernmentArea, Ward, PollingUnit, ElectionResult, WardResult,
)

DATA_FILE = os.path.join(os.path.dirname(__file__), 'taraba_pus.json')
STATE_CODE = '34'


def norm(s):
    return ' '.join((s or '').lower().replace('-', ' ').split())


@transaction.atomic
def run():
    with open(DATA_FILE, encoding='utf-8') as f:
        data = json.load(f)

    # Existing LGAs keyed by normalized name (kept, not deleted)
    lga_by_norm = {norm(l.name): l for l in LocalGovernmentArea.objects.all()}

    # --- WIPE ---
    er = ElectionResult.objects.all().delete()
    wr = WardResult.objects.all().delete()
    pu = PollingUnit.objects.all().delete()
    wd = Ward.objects.all().delete()
    print(f"Wiped -> wards:{wd[0]}  polling_units:{pu[0]}  "
          f"results:{er[0]}  ward_overrides:{wr[0]}\n")

    n_lga = n_ward = n_pu = 0
    summary = []

    for L in data['lgas']:
        key = norm(L['name'])
        lga = lga_by_norm.get(key)
        if not lga:
            lga = LocalGovernmentArea.objects.create(
                name=L['name'].title(), code=L.get('code')
            )
            lga_by_norm[key] = lga
            print(f"  + created LGA {lga.name}")
        n_lga += 1

        lga_pu = 0
        for W in L['wards']:
            ward = Ward.objects.create(
                name=W['name'], lga=lga, code=f"{L['code']}-{W['code']}"
            )
            n_ward += 1

            rows = []
            seen = set()
            for U in W['units']:
                name = U['name']
                # keep PU names unique within a ward (unique_together = name, ward)
                if name in seen:
                    name = f"{name} [{U['code']}]"
                seen.add(name)
                rows.append(PollingUnit(
                    name=name,
                    ward=ward,
                    code=f"{STATE_CODE}-{L['code']}-{W['code']}-{U['code']}",
                ))
            PollingUnit.objects.bulk_create(rows, batch_size=500)
            n_pu += len(rows)
            lga_pu += len(rows)

        summary.append((lga.name, len(L['wards']), lga_pu))

    # ---- Report ----
    print("=== Imported (per LGA) ===")
    for name, wcount, pcount in summary:
        print(f"  {name:<16} wards={wcount:<3} polling_units={pcount}")
    print("  " + "-" * 34)
    print(f"  LGAs={n_lga}  wards={n_ward}  polling_units={n_pu}")
    print("\nDone. Structure rebuilt from the modern INEC dataset.")
    print("Next: run  python seed_results.py  to repopulate vote results.")


if __name__ == '__main__':
    run()
