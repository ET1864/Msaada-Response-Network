from django.contrib import admin
from .models import Request, Shelter


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ("reference_code", "location", "need_type", "people_count", "priority", "status")
    readonly_fields = ("reference_code",)


admin.site.register(Shelter)