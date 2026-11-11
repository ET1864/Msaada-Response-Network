from django.contrib import admin

from .models import Incident, Item, Request, RequestItem, ResourceOffer, Shelter


class RequestItemInline(admin.TabularInline):
    model = RequestItem
    extra = 0


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ("reference_code", "incident", "location", "need_type", "people_count", "priority", "status")
    list_filter = ("status", "priority", "incident")
    readonly_fields = ("reference_code",)
    inlines = [RequestItemInline]


@admin.register(Shelter)
class ShelterAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "capacity", "occupancy")


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("name", "hazard_type", "area", "status", "opened_at", "closed_at")
    list_filter = ("status", "hazard_type")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "unit", "hazard_types")
    list_filter = ("category",)


@admin.register(ResourceOffer)
class ResourceOfferAdmin(admin.ModelAdmin):
    list_display = ("item", "offered_by", "quantity_available", "location", "valid_until", "status")
    list_filter = ("status", "incident")
