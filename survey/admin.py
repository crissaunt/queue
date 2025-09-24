from django.contrib import admin
from .models import ClientType, CCchoices, CCquestion, ServiceQualityDimension, SatisfactionSurvey


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




