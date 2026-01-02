"""
Management command to add polling units for a Ward
Usage: python manage.py add_polling_units <lga_name> <ward_name> <pu1> <pu2> ... <puN>
"""
from django.core.management.base import BaseCommand
from election.models import LocalGovernmentArea, Ward, PollingUnit


class Command(BaseCommand):
    help = 'Add polling units to a Ward'

    def add_arguments(self, parser):
        parser.add_argument(
            'lga_name',
            type=str,
            help='Name of the Local Government Area'
        )
        parser.add_argument(
            'ward_name',
            type=str,
            help='Name of the Ward'
        )
        parser.add_argument(
            '--polling-units',
            nargs='+',
            help='List of polling unit names (space-separated)',
        )

    def handle(self, *args, **options):
        lga_name = options['lga_name']
        ward_name = options['ward_name']
        polling_units_list = options.get('polling_units', [])

        # Get LGA
        try:
            lga = LocalGovernmentArea.objects.get(name__iexact=lga_name)
        except LocalGovernmentArea.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'LGA "{lga_name}" not found.'))
            return

        # Get Ward
        try:
            ward = Ward.objects.get(name__iexact=ward_name, lga=lga)
        except Ward.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Ward "{ward_name}" not found in {lga_name}.'))
            self.stdout.write(f'Available wards in {lga_name}:')
            for w in Ward.objects.filter(lga=lga):
                self.stdout.write(f'  - {w.name}')
            return

        if not polling_units_list:
            self.stdout.write(self.style.ERROR('No polling units provided. Use --polling-units option.'))
            return

        # Add polling units
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for index, pu_name in enumerate(polling_units_list, start=1):
            # Extract polling unit name and code if provided in format "NAME CODE"
            parts = pu_name.strip().split(',')
            pu_name_clean = parts[0].strip()
            
            # Try to extract code from the name or use index
            code_parts = pu_name_clean.split()
            if len(code_parts) >= 2 and code_parts[-1].isdigit() and len(code_parts[-1]) == 3:
                # Last part is a 3-digit code
                pu_code = code_parts[-1]
                pu_name_clean = ' '.join(code_parts[:-1])
            else:
                # Use index padded to 3 digits
                pu_code = str(index).zfill(3)

            polling_unit, created = PollingUnit.objects.get_or_create(
                name=pu_name_clean,
                ward=ward,
                defaults={'code': pu_code}
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  + Created: {pu_name_clean} (Code: {pu_code})'))
            else:
                if polling_unit.code != pu_code:
                    polling_unit.code = pu_code
                    polling_unit.save()
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f'  ~ Updated: {pu_name_clean} (Code: {pu_code})'))
                else:
                    skipped_count += 1
                    self.stdout.write(self.style.NOTICE(f'  - Skipped: {pu_name_clean} (already exists)'))

        self.stdout.write(self.style.SUCCESS(
            f'\nSummary: Created {created_count}, Updated {updated_count}, Skipped {skipped_count}'
        ))


