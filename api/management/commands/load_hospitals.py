from django.core.management.base import BaseCommand
from api.models import Hospital


class Command(BaseCommand):
    help = 'Load initial hospital data for Bishkek'

    def handle(self, *args, **kwargs):
        hospitals_data = [
            {"name": "Bishkek City Clinical Hospital No. 1", "lat": 42.875144, "lng": 74.562028},
            {"name": "National Hospital", "lat": 42.875086, "lng": 74.598375},
            {"name": "City Clinical Hospital No. 4 (Emergency)", "lat": 42.846505, "lng": 74.604471},
            {"name": "National Center of Cardiology", "lat": 42.874136, "lng": 74.598918},
            {"name": "Kyrgyz National Oncology Center", "lat": 42.83965, "lng": 74.61374},
            {"name": "Children's Hospital #3", "lat": 42.840278, "lng": 74.606667},
            {"name": "Ala-Too Hospital", "lat": 42.837880, "lng": 74.568470},
            {"name": "Azmi Hospital", "lat": 42.883792, "lng": 74.629818},
            {"name": "Life Hospital", "lat": 42.872714, "lng": 74.582845},
            {"name": "M.A.G Clinic", "lat": 42.868779, "lng": 74.614392}
        ]

        created_count = 0
        for hospital_data in hospitals_data:
            hospital, created = Hospital.objects.get_or_create(
                name=hospital_data['name'],
                defaults={
                    'latitude': hospital_data['lat'],
                    'longitude': hospital_data['lng'],
                    'is_active': True
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created hospital: {hospital.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Hospital already exists: {hospital.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully loaded {created_count} new hospitals')
        )
