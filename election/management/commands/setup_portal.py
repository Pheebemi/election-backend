"""Fill an empty database with what the portal needs to start: the parties
(with their logos) and the 16 LGAs, 168 wards and 3,597 polling units of
Taraba State (main dataset).

Safe to run on every deploy: it only adds what is missing and never touches
existing wards, polling units or results.

    python manage.py setup_portal
"""
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from election.models import LocalGovernmentArea, PoliticalParty, PollingUnit, Ward

ROOT = Path(settings.BASE_DIR)
DATASET = 'main'
STATE_CODE = '34'


def norm(s):
    return ' '.join((s or '').lower().replace('-', ' ').split())


class Command(BaseCommand):
    help = 'Add the parties and the Taraba LGAs, wards and polling units if they are missing.'

    @transaction.atomic
    def handle(self, *args, **options):
        seed = json.loads((ROOT / 'restore_data.json').read_text(encoding='utf-8'))

        for row in seed:
            if row['model'] != 'election.politicalparty':
                continue
            f = row['fields']
            _, created = PoliticalParty.objects.get_or_create(
                abbreviation=f['abbreviation'],
                defaults={'name': f['name'], 'color': f['color'], 'logo': f['logo']},
            )
            if created:
                self.stdout.write(f"  + party {f['abbreviation']}")

        if Ward.objects.filter(dataset=DATASET).exists():
            self.stdout.write('Polling-unit structure already present - left as is.')
            return

        # LGA names as the portal has always shown them (e.g. "Ardo-kola").
        names = {norm(r['fields']['name']): r['fields'] for r in seed
                 if r['model'] == 'election.localgovernmentarea'}
        lgas = {norm(l.name): l for l in LocalGovernmentArea.objects.filter(dataset=DATASET)}
        data = json.loads((ROOT / 'taraba_pus.json').read_text(encoding='utf-8'))
        n_ward = n_pu = 0
        for L in data['lgas']:
            key = norm(L['name'])
            lga = lgas.get(key) or LocalGovernmentArea.objects.create(
                name=names.get(key, {}).get('name') or L['name'].title(),
                code=L.get('code'), dataset=DATASET,
            )
            for W in L['wards']:
                ward = Ward.objects.create(name=W['name'], lga=lga, code=f"{L['code']}-{W['code']}")
                n_ward += 1
                seen, rows = set(), []
                for U in W['units']:
                    name = U['name'] if U['name'] not in seen else f"{U['name']} [{U['code']}]"
                    seen.add(name)
                    rows.append(PollingUnit(name=name, ward=ward, dataset=DATASET,
                                            code=f"{STATE_CODE}-{L['code']}-{W['code']}-{U['code']}"))
                PollingUnit.objects.bulk_create(rows, batch_size=500)
                n_pu += len(rows)
        self.stdout.write(self.style.SUCCESS(f'Added {n_ward} wards and {n_pu} polling units.'))
