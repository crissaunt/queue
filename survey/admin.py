from django.contrib import admin
from .models import (
    ClientType, CCchoices, CCquestion, ServiceQualityDimension,
    SatisfactionSurvey, SQDResponse, CCResponse,
    QuestionYear, SQDYear, SurveyYear
)


# =========================
# BASIC MODELS
# =========================
@admin.register(ClientType)
class ClientTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(CCquestion)
class CCquestionAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")  # ✅ include created_at
    readonly_fields = ("created_at",)


@admin.register(CCchoices)
class CCchoicesAdmin(admin.ModelAdmin):
    list_display = ("name", "question", "created_at")
    list_filter = ("question",)
    readonly_fields = ("created_at",)


@admin.register(ServiceQualityDimension)
class ServiceQualityDimensionAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    readonly_fields = ("created_at",)
    


@admin.register(SurveyYear)
class SurveyYearAdmin(admin.ModelAdmin):
    list_display = ("year",)
    ordering = ("-year",)


# =========================
# MAPPING TABLES (Year links)
# =========================
@admin.register(QuestionYear)
class QuestionYearAdmin(admin.ModelAdmin):
    list_display = ("year", "question")
    list_filter = ("year",)


@admin.register(SQDYear)
class SQDYearAdmin(admin.ModelAdmin):
    list_display = ("year", "sqd")
    list_filter = ("year",)


# =========================
# SURVEY + RESPONSES
# =========================
@admin.register(SatisfactionSurvey)
class SatisfactionSurveyAdmin(admin.ModelAdmin):
    list_display = ("id", "survey_year", "client_type", "visit_date", "submitted_at")
    list_filter = ("survey_year", "client_type", "sex", "region")
    search_fields = ("code__id", "office_person", "service_availed", "feedback", "email")


@admin.register(CCResponse)
class CCResponseAdmin(admin.ModelAdmin):
    list_display = ('survey', 'get_question', 'choice', 'created_at')
    readonly_fields = ("created_at",)

    def get_question(self, obj):
        return obj.question_year.question.name
    get_question.short_description = "Question"



@admin.register(SQDResponse)
class SQDResponseAdmin(admin.ModelAdmin):
    list_display = ("survey", "sqd_year", "rating", "created_at")
    readonly_fields = ("created_at",)
