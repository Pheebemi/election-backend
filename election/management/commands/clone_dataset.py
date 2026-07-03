from django.core.management.base import BaseCommand
from django.db import transaction

from election.models import LocalGovernmentArea, Ward, PollingUnit


class Command(BaseCommand):
    help = (
        "Copy the LGA / Ward / Polling Unit structure from one dataset into another. "
        "Election results are NOT copied (the target dataset starts empty). "
        "Parties are shared across all datasets, so they are left untouched."
    )

    def add_arguments(self, parser):
        parser.add_argument('--source', default='main', help="Dataset to copy from (default: main)")
        parser.add_argument('--target', default='apc', help="Dataset to copy into (default: apc)")
        parser.add_argument(
            '--wipe', action='store_true',
            help="Delete any existing structure in the target dataset first (cascades to its results).",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        source = opts['source']
        target = opts['target']

        if source == target:
            self.stderr.write("source and target must be different")
            return

        if opts['wipe']:
            deleted, _ = LocalGovernmentArea.objects.filter(dataset=target).delete()
            self.stdout.write(f"Wiped {deleted} existing '{target}' rows (cascade).")
        elif LocalGovernmentArea.objects.filter(dataset=target).exists():
            self.stderr.write(
                f"Target dataset '{target}' already has data. Re-run with --wipe to replace it."
            )
            return

        lga_count = ward_count = pu_count = 0

        for lga in LocalGovernmentArea.objects.filter(dataset=source):
            new_lga = LocalGovernmentArea.objects.create(
                name=lga.name, code=lga.code, dataset=target,
            )
            lga_count += 1

            for ward in lga.wards.all():
                new_ward = Ward(name=ward.name, code=ward.code, lga=new_lga)
                new_ward.save()  # save() syncs dataset from the LGA
                ward_count += 1

                pus = [
                    PollingUnit(
                        name=pu.name, code=pu.code,
                        registered_voters=pu.registered_voters, ward=new_ward,
                        dataset=target,
                    )
                    for pu in ward.polling_units.all()
                ]
                PollingUnit.objects.bulk_create(pus)
                pu_count += len(pus)

        self.stdout.write(self.style.SUCCESS(
            f"Cloned '{source}' -> '{target}': "
            f"{lga_count} LGAs, {ward_count} wards, {pu_count} polling units. "
            f"Election results start empty."
        ))
