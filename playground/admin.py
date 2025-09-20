from django.contrib import admin
from .models import SatisfactionSurvey, Pin

@admin.register(SatisfactionSurvey)
class SatisfactionSurveyAdmin(admin.ModelAdmin):
    list_display = ("pin", "clientType", "government", "visitDate", "sex", "age", "region", "submitted_at")
    search_fields = ("clientType", "government", "region", "officePerson", "serviceAvailed")
    list_filter = ("clientType", "government", "sex", "region", "visitDate")
    ordering = ("-submitted_at",)

@admin.register(Pin)
class PinAdmin(admin.ModelAdmin):
    list_display = ("id", "code")
    search_fields = ("code",)
    ordering = ("id",)
