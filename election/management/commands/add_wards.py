"""
Management command to add wards for a Local Government Area
Usage: python manage.py add_wards <lga_name> <ward1> <ward2> ... <wardN>
Or use the interactive mode: python manage.py add_wards
"""
from django.core.management.base import BaseCommand
from election.models import LocalGovernmentArea, Ward


class Command(BaseCommand):
    help = 'Add wards to a Local Government Area'

    def add_arguments(self, parser):
        parser.add_argument(
            'lga_name',
            type=str,
            help='Name of the Local Government Area'
        )
        parser.add_argument(
            '--wards',
            nargs='+',
            help='List of ward names (space-separated)',
        )
        parser.add_argument(
            '--file',
            type=str,
            help='Path to a file containing ward names (one per line)',
        )

    def handle(self, *args, **options):
        lga_name = options['lga_name']
        wards_list = options.get('wards', [])
        file_path = options.get('file')

        # Get or create LGA
        try:
            lga = LocalGovernmentArea.objects.get(name__iexact=lga_name)
            self.stdout.write(self.style.SUCCESS(f'Found LGA: {lga.name}'))
        except LocalGovernmentArea.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'LGA "{lga_name}" not found.'))
            self.stdout.write('Available LGAs:')
            for lga in LocalGovernmentArea.objects.all():
                self.stdout.write(f'  - {lga.name}')
            return

        # Get wards from file if provided
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    wards_list = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
                return

        if not wards_list:
            self.stdout.write(self.style.ERROR('No wards provided. Use --wards or --file option.'))
            return

        # Add wards
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for index, ward_name in enumerate(wards_list, start=1):
            # Extract ward name and code if provided in format "NAME CODE"
            parts = ward_name.strip().split()
            if len(parts) >= 2 and parts[-1].isdigit():
                # Last part is a number (code)
                ward_code = parts[-1].zfill(2)  # Pad to 2 digits
                ward_name_clean = ' '.join(parts[:-1])
            else:
                # No code provided, use index
                ward_code = str(index).zfill(2)
                ward_name_clean = ward_name.strip()

            ward, created = Ward.objects.get_or_create(
                name=ward_name_clean,
                lga=lga,
                defaults={'code': ward_code}
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  + Created: {ward_name_clean} (Code: {ward_code})'))
            else:
                if ward.code != ward_code:
                    ward.code = ward_code
                    ward.save()
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f'  ~ Updated: {ward_name_clean} (Code: {ward_code})'))
                else:
                    skipped_count += 1
                    self.stdout.write(self.style.NOTICE(f'  - Skipped: {ward_name_clean} (already exists)'))

        self.stdout.write(self.style.SUCCESS(
            f'\nSummary: Created {created_count}, Updated {updated_count}, Skipped {skipped_count}'
        ))

