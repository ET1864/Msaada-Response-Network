from datetime import timedelta

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Incident, Item, Request, ResourceOffer, Shelter

# (category, name, unit, hazard tags; blank means relevant to every hazard)
CATALOGUE = [
    ("water", "Drinking water", "litres", ""),
    ("water", "Water for washing", "litres", ""),
    ("water", "Water treatment tablets", "packs", "flood"),
    ("water", "Water trucking", "trips", "drought"),
    ("food", "Cooked meals", "meals", ""),
    ("food", "Food rations", "packs", ""),
    ("food", "Livestock feed", "bags", "drought"),
    ("shelter", "Place in a shelter", "people", ""),
    ("shelter", "Tent", "units", ""),
    ("shelter", "Blankets", "units", ""),
    ("medical", "First aid", "people", ""),
    ("medical", "Medical supplies", "packs", ""),
    ("medical", "Mosquito nets", "units", "flood"),
    ("clothing_hygiene", "Clothing", "sets", ""),
    ("clothing_hygiene", "Hygiene kit", "kits", ""),
    ("transport", "Boat transport", "trips", "flood"),
    ("transport", "Vehicle transport", "trips", ""),
]


class Command(BaseCommand):
    help = "Create demo data: Organization group, item catalogue, a demo incident, shelters, offers and requests."

    def handle(self, *args, **options):
        Group.objects.get_or_create(name="Organization")

        for category, name, unit, tags in CATALOGUE:
            Item.objects.get_or_create(
                category=category, name=name,
                defaults={"unit": unit, "hazard_types": tags},
            )

        incident, _ = Incident.objects.get_or_create(
            name="Kisumu floods 2026",
            defaults={"hazard_type": "flood", "area": "Kisumu County", "status": "Active"},
        )

        Shelter.objects.get_or_create(
            name="Kondele Community Hall (demo)",
            defaults={"location": "Kondele, Kisumu", "capacity": 200, "occupancy": 45,
                      "assistance_available": "Meals, blankets, first aid"},
        )
        Shelter.objects.get_or_create(
            name="Mamboleo Primary School (demo)",
            defaults={"location": "Mamboleo, Kisumu", "capacity": 150, "occupancy": 80,
                      "assistance_available": "Shelter, water"},
        )

        if ResourceOffer.objects.count() == 0:
            until = timezone.now() + timedelta(hours=72)
            demo_offers = [
                ("Drinking water", "Demo Relief Group", 5000, "Kondele, Kisumu"),
                ("Place in a shelter", "Demo Relief Group", 120, "Kondele Community Hall"),
                ("Boat transport", "Demo Rescue Volunteers", 6, "Kisumu lakeshore"),
                ("Mosquito nets", "Demo Health Partners", 300, "Mamboleo, Kisumu"),
            ]
            for item_name, org, qty, place in demo_offers:
                ResourceOffer.objects.create(
                    incident=incident,
                    item=Item.objects.get(name=item_name),
                    offered_by=org, contact_phone="0700000000",
                    quantity_available=qty, location=place,
                    valid_until=until, status="Active",
                )

        if Request.objects.count() < 3:
            demo_requests = [
                ("Demo Amina (demo)", "0700000001", "shelter", 4, "Mamboleo, Kisumu", "High", "Pending"),
                ("Demo Peter (demo)", "0700000002", "food_water", 6, "Kondele, Kisumu", "Medium", "Under Review"),
                ("Demo Grace (demo)", "0700000003", "medical", 2, "Nyalenda, Kisumu", "High", "Pending"),
            ]
            for name, phone, need, people, place, priority, status in demo_requests:
                Request.objects.create(
                    incident=incident, submitted_by_name=name, phone=phone,
                    need_type=need, people_count=people, location=place,
                    priority=priority, status=status,
                )

        self.stdout.write(self.style.SUCCESS(
            "Demo data ready. Create an organization user in the admin and add them to the 'Organization' group."
        ))
