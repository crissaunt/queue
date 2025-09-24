from django.contrib import admin
from .models import  RequestType, Courses, Appointments, Personel, Code

# from .models import students

# Register your models here.
# class StudentsAdmin(admin.ModelAdmin):
#     list_display=('student_fname','student_mname','student_lname' )

class AppointmentsAdmin(admin.ModelAdmin):
    list_display=('firstName','ticket_number' ,'status','is_priority','skip_until', 'skip_count')  
    def get_category(self, obj):
        return obj.category  
    get_category.short_description = 'Category'
admin.site.register(Appointments,AppointmentsAdmin)


class RequestTypeAdmin(admin.ModelAdmin):
    list_display=('request',)   
admin.site.register(RequestType, RequestTypeAdmin)
 

class CoursesAdmin(admin.ModelAdmin):
    list_display = ('courses',)   
admin.site.register(Courses, CoursesAdmin)

class PersonelAdmin(admin.ModelAdmin):
    list_display= ('user',)
admin.site.register(Personel, PersonelAdmin)


class CodeAdmin(admin.ModelAdmin):
    list_display= ('code',)
admin.site.register(Code, CodeAdmin)








# admin.site.register(students,StudentsAdmin)







