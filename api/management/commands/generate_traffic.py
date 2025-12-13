from django.core.management.base import BaseCommand
from api.models import TrafficData
import random


class Command(BaseCommand):
    help = 'Generate initial traffic data for Bishkek streets'

    def handle(self, *args, **kwargs):
        streets = [
            {"name": "Sovetskaya Street", "start": [42.8200, 74.6090], "end": [42.8950, 74.6090]},
            {"name": "Akhunbaev Street", "start": [42.8430, 74.5600], "end": [42.8430, 74.6700]},
            {"name": "7 April Street", "start": [42.8200, 74.6480], "end": [42.9000, 74.6480]},
            {"name": "Chuy Avenue", "start": [42.8750, 74.5500], "end": [42.8750, 74.6800]},
            {"name": "Manas Avenue", "start": [42.8100, 74.5870], "end": [42.8800, 74.5870]},
            {"name": "Jibek Jolu Avenue", "start": [42.8940, 74.5500], "end": [42.8940, 74.6800]},
            {"name": "Suerkulov Street", "start": [42.8380, 74.6000], "end": [42.8380, 74.6400]},
            {"name": "Elebesova Street", "start": [42.9000, 74.6150], "end": [42.9300, 74.6150]},
            {"name": "Gorkiy Street", "start": [42.8560, 74.5800], "end": [42.8560, 74.6400]},
            {"name": "Kievskaya Street", "start": [42.8730, 74.5700], "end": [42.8730, 74.6300]},
            {"name": "Moskovskaya Street", "start": [42.8690, 74.5700], "end": [42.8690, 74.6300]},
            {"name": "Bokonbaeva Street", "start": [42.8640, 74.5700], "end": [42.8640, 74.6500]},
            {"name": "Lev Tolstoy Street", "start": [42.8580, 74.5500], "end": [42.8580, 74.6800]},
            {"name": "Molodaya Gvardiya", "start": [42.8600, 74.5650], "end": [42.9000, 74.5650]},
            {"name": "Toktogul Street", "start": [42.8650, 74.5800], "end": [42.8650, 74.6200]},
            {"name": "Isanov Street", "start": [42.8800, 74.5900], "end": [42.8800, 74.6300]},
            {"name": "Razzakov Street", "start": [42.8500, 74.5900], "end": [42.8500, 74.6200]},
            {"name": "Ibraimov Street", "start": [42.8420, 74.5800], "end": [42.8420, 74.6100]},
        ]

        created_count = 0
        updated_count = 0

        for street in streets:
            # Generate random traffic data
            congestion = random.randint(0, 100)
            speed = max(10, 60 - (congestion * 0.5))  # Speed decreases with congestion
            
            traffic, created = TrafficData.objects.update_or_create(
                street_name=street['name'],
                defaults={
                    'start_latitude': street['start'][0],
                    'start_longitude': street['start'][1],
                    'end_latitude': street['end'][0],
                    'end_longitude': street['end'][1],
                    'congestion_percentage': congestion,
                    'average_speed': speed,
                    'is_active': True
                }
            )
            
            # Update traffic level based on congestion
            traffic.update_traffic_level()
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Created: {street["name"]} - {traffic.get_traffic_level_display()} ({congestion}%)'
                    )
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'Updated: {street["name"]} - {traffic.get_traffic_level_display()} ({congestion}%)'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Traffic data loaded: {created_count} created, {updated_count} updated'
            )
        )
