from django.db import models
from django.utils import timezone


class Request(models.Model):
    NEED_CHOICES = [
        ("food_water", "Food and water"),
        ("shelter", "Shelter and accommodation"),
        ("medical", "Medical assistance"),
        ("clothing", "Clothing and hygiene items"),
        ("transport", "Transport and evacuation"),
        ("other", "Other essential needs"),
    ]
    PRIORITY_CHOICES = [
        ("High", "High"),
        ("Medium", "Medium"),
        ("Low", "Low"),
    ]
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Under Review", "Under Review"),
        ("Approved", "Approved"),
        ("In Progress", "In Progress"),
        ("Fulfilled", "Fulfilled"),
        ("Redirected", "Redirected"),
    ]

    reference_code = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    submitted_by_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    for_someone_else = models.BooleanField(default=False)
    beneficiary_name = models.CharField(max_length=100, blank=True)
    relationship = models.CharField(max_length=50, blank=True)
    need_type = models.CharField(max_length=20, choices=NEED_CHOICES)
    people_count = models.PositiveIntegerField(default=1)
    location = models.CharField(max_length=200)
    additional_info = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="Medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.reference_code:
            self.reference_code = f"MSA-{timezone.now().year}-{self.pk:04d}"
            super().save(update_fields=["reference_code"])

    def __str__(self):
        return f"{self.reference_code} - {self.location}"


class Shelter(models.Model):
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    capacity = models.PositiveIntegerField()
    occupancy = models.PositiveIntegerField(default=0)
    assistance_available = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name