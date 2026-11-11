from django.db import models
from django.utils import timezone
from datetime import timedelta


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
    incident = models.ForeignKey("Incident", null=True, blank=True, on_delete=models.SET_NULL, related_name="requests")
    other_need = models.CharField(max_length=300, blank=True)
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

def default_valid_until():
    return timezone.now() + timedelta(hours=72)


class Incident(models.Model):
    HAZARD_CHOICES = [
        ("flood", "Flood"),
        ("landslide", "Landslide"),
        ("drought", "Drought"),
        ("fire", "Fire"),
        ("disease", "Disease outbreak"),
        ("other", "Other"),
    ]
    STATUS_CHOICES = [("Active", "Active"), ("Closed", "Closed")]

    name = models.CharField(max_length=120)
    hazard_type = models.CharField(max_length=20, choices=HAZARD_CHOICES)
    area = models.CharField(max_length=150)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Active")
    opened_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == "Closed" and self.closed_at is None:
            self.closed_at = timezone.now()
        if self.status == "Active":
            self.closed_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.get_hazard_type_display()})"


class Item(models.Model):
    CATEGORY_CHOICES = [
        ("water", "Water"),
        ("food", "Food"),
        ("shelter", "Shelter"),
        ("medical", "Medical"),
        ("clothing_hygiene", "Clothing and hygiene"),
        ("transport", "Transport and evacuation"),
        ("other", "Other"),
    ]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=30)
    hazard_types = models.CharField(
        max_length=100, blank=True,
        help_text="Hazards this item is most relevant to, separated by commas "
                  "(flood, landslide, drought, fire, disease, other). Leave blank if it applies to all.",
    )

    class Meta:
        ordering = ["category", "name"]

    def relevant_for(self, hazard_type):
        tags = [t.strip() for t in self.hazard_types.split(",") if t.strip()]
        return not tags or hazard_type in tags

    def __str__(self):
        return f"{self.name} ({self.unit})"


class ResourceOffer(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending verification"),
        ("Active", "Active"),
        ("Exhausted", "Exhausted"),
        ("Expired", "Expired"),
    ]

    incident = models.ForeignKey(Incident, null=True, blank=True, on_delete=models.SET_NULL, related_name="offers")
    item = models.ForeignKey(Item, on_delete=models.PROTECT, related_name="offers")
    offered_by = models.CharField(max_length=120)
    contact_phone = models.CharField(max_length=20)
    quantity_available = models.PositiveIntegerField()
    location = models.CharField(max_length=200)
    valid_until = models.DateTimeField(default=default_valid_until)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        return self.status == "Active" and self.quantity_available > 0 and self.valid_until > timezone.now()

    def __str__(self):
        return f"{self.item.name}: {self.quantity_available} {self.item.unit} ({self.offered_by})"

class RequestItem(models.Model):
    help_request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="lines")
    offer = models.ForeignKey(ResourceOffer, null=True, blank=True, on_delete=models.SET_NULL, related_name="request_lines")
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    reserved = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.item.name} x {self.quantity} ({self.help_request.reference_code})"