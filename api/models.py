from django.db import models
from django.utils import timezone


class Hospital(models.Model):
    """Hospital model for storing hospital information"""
    name = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    ambulance_count = models.IntegerField(default=5, help_text='Number of available ambulances')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Hospital'
        verbose_name_plural = 'Hospitals'

    def __str__(self):
        return self.name


class Route(models.Model):
    """Route model for storing route calculations"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    start_latitude = models.FloatField()
    start_longitude = models.FloatField()
    end_latitude = models.FloatField()
    end_longitude = models.FloatField()
    hospital = models.ForeignKey(Hospital, on_delete=models.SET_NULL, null=True, blank=True)
    distance = models.FloatField(help_text='Distance in kilometers')
    duration = models.IntegerField(help_text='Duration in minutes')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    traffic_enabled = models.BooleanField(default=True)
    route_data = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Route'
        verbose_name_plural = 'Routes'

    def __str__(self):
        return f"Route {self.id} - {self.status}"


class TrafficData(models.Model):
    """Traffic data for streets"""
    TRAFFIC_LEVEL_CHOICES = [
        ('free', 'Free Flow'),      # Green - 0-30% congestion
        ('light', 'Light Traffic'),  # Yellow - 30-50% congestion
        ('moderate', 'Moderate'),    # Orange - 50-70% congestion
        ('heavy', 'Heavy Traffic'),  # Red - 70-90% congestion
        ('jam', 'Traffic Jam'),      # Dark Red - 90-100% congestion
    ]

    street_name = models.CharField(max_length=255)
    start_latitude = models.FloatField()
    start_longitude = models.FloatField()
    end_latitude = models.FloatField()
    end_longitude = models.FloatField()
    traffic_level = models.CharField(max_length=20, choices=TRAFFIC_LEVEL_CHOICES, default='free')
    congestion_percentage = models.IntegerField(default=0, help_text='0-100%')
    average_speed = models.FloatField(help_text='km/h', default=50.0)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['street_name']
        verbose_name = 'Traffic Data'
        verbose_name_plural = 'Traffic Data'

    def __str__(self):
        return f"{self.street_name} - {self.get_traffic_level_display()}"

    def get_color(self):
        """Return color code for traffic level"""
        colors = {
            'free': '#22c55e',      # Green
            'light': '#eab308',     # Yellow
            'moderate': '#f97316',  # Orange
            'heavy': '#ef4444',     # Red
            'jam': '#991b1b',       # Dark Red
        }
        return colors.get(self.traffic_level, '#22c55e')

    def update_traffic_level(self):
        """Update traffic level based on congestion percentage"""
        if self.congestion_percentage < 30:
            self.traffic_level = 'free'
        elif self.congestion_percentage < 50:
            self.traffic_level = 'light'
        elif self.congestion_percentage < 70:
            self.traffic_level = 'moderate'
        elif self.congestion_percentage < 90:
            self.traffic_level = 'heavy'
        else:
            self.traffic_level = 'jam'
        self.save()
