from django.contrib import admin
from .models import  UserType,  RequestType, Courses, UserType, StudentAppointments, Personel, Survey

# from .models import students

# Register your models here.
# class StudentsAdmin(admin.ModelAdmin):
#     list_display=('student_fname','student_mname','student_lname' )

class StudentAppointmentsAdmin(admin.ModelAdmin):
    list_display=('idNumber' ,'firstName','ticket_number' ,'status','is_priority','skip_until', 'skip_count')  
    def get_category(self, obj):
        return obj.category  
    get_category.short_description = 'Category'
admin.site.register(StudentAppointments,StudentAppointmentsAdmin)

class UserTypeAdmin(admin.ModelAdmin):
    list_display=('name', )   
admin.site.register(UserType, UserTypeAdmin)


class RequestTypeAdmin(admin.ModelAdmin):
    list_display=('request',)   
admin.site.register(RequestType, RequestTypeAdmin)
 

class CoursesAdmin(admin.ModelAdmin):
    list_display = ('courses',)   
admin.site.register(Courses, CoursesAdmin)

class PersonelAdmin(admin.ModelAdmin):
    list_display= ('username',)
admin.site.register(Personel, PersonelAdmin)


class SurveyAdmin(admin.ModelAdmin):
    list_display= ('student_appointment','code',)
admin.site.register(Survey, SurveyAdmin)





# admin.site.register(students,StudentsAdmin)







