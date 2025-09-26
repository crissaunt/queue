from django.contrib import admin
from .models import ClientType, CCchoices, CCquestion, ServiceQualityDimension, SatisfactionSurvey, SQDResponse, CCResponse


class ClientTypeAdmin(admin.ModelAdmin):
    list_display=('name',)   
admin.site.register(ClientType, ClientTypeAdmin)


class CCchoicesAdmin(admin.ModelAdmin):
    list_display=('name', 'question')   
admin.site.register(CCchoices, CCchoicesAdmin)



class CCquestionAdmin(admin.ModelAdmin):
    list_display = ( 'name',)
admin.site.register(CCquestion, CCquestionAdmin)


class ServiceQualityDimensioneAdmin(admin.ModelAdmin):
    list_display=('name',)   
admin.site.register(ServiceQualityDimension, ServiceQualityDimensioneAdmin)


class SatisfactionSurveyAdmin(admin.ModelAdmin):
    list_display=('code',)   
admin.site.register(SatisfactionSurvey, SatisfactionSurveyAdmin)


class SQDResponseAdmin(admin.ModelAdmin):
    list_display = ('survey', 'sqd', 'rating')
admin.site.register(SQDResponse, SQDResponseAdmin)  # ✅ correct model

class CCResponseAdmin(admin.ModelAdmin):
    list_display = ('survey', 'question', 'get_choices')

    def get_choices(self, obj):
        return ", ".join([choice.name for choice in obj.choices.all()])
    get_choices.short_description = "Choices"
admin.site.register(CCResponse, CCResponseAdmin)  # ✅ correct model






