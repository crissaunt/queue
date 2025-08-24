from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import loader
from personel.models import StudentAppointments, RequestType, Courses,UserType
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import localtime
from django.http import JsonResponse


now_ph = localtime(timezone.now())
today = now_ph.date() 

def home(request):
    courses = Courses.objects.all()
    requests = RequestType.objects.all()
  # last 10

    template = loader.get_template('students/home.html')
    context = {
        'courses': courses,
        'requests': requests,
    
    }
    return HttpResponse(template.render(context, request))




def student_submit(request):
    if request.method == "POST":
        id_number = request.POST.get("idNumber")
        first_name = request.POST.get("firstName")
        middle_name = request.POST.get("middleName")
        last_name = request.POST.get("lastName")
        course_id = request.POST.get("course")
        request_id = request.POST.get("request")
        is_priority = "yes" if request.POST.get("is_priority") else "no"

        # Get related objects safely
        course = Courses.objects.filter(id=course_id).first()
        user_type = UserType.objects.filter(name='student').first()
        request_type = RequestType.objects.filter(id=request_id).first()

        # ----- Generate ticket number -----
        if is_priority == "yes":
            prefix = "P"
            last_ticket = StudentAppointments.objects.filter(is_priority="yes").order_by("-id").first()
        else:
            prefix = "S"
            last_ticket = StudentAppointments.objects.filter(is_priority="no").order_by("-id").first()

        if last_ticket and last_ticket.ticket_number:
            try:
                last_num = int(last_ticket.ticket_number.split("-")[-1])
            except:
                last_num = 0
        else:
            last_num = 0

        new_ticket_number = f"{prefix}-{last_num + 1:03d}"

        # Save appointment
        student = StudentAppointments.objects.create(
            idNumber=id_number,
            firstName=first_name,
            middleName=middle_name,
            lastName=last_name,
            courses=course,
            requestType=request_type,
            ticket_number=new_ticket_number,
            status="pending",
            userType=user_type,
            is_priority=is_priority,
            datetime=today,
        )
        return JsonResponse({"success": True, "ticket": student.ticket_number})

        return redirect("home")



    




