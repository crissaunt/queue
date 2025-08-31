from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import loader
from personel.models import StudentAppointments, RequestType, Courses, Survey
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import localtime
from django.http import JsonResponse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import random, string



now_ph = localtime(timezone.now())
today = now_ph.date() 

from django.utils.timezone import localtime

from django.db.models import Q

def broadcast_queue_update():
    now_ph = localtime(timezone.now())
    today = now_ph.date()

    non_priority_count = StudentAppointments.objects.filter(
        Q(status="pending") | Q(status="skip"),
        is_priority="no",
        datetime__date=today
    ).count()

    priority_count = StudentAppointments.objects.filter(
        Q(status="pending") | Q(status="skip"),
        is_priority="yes",
        datetime__date=today
    ).count()

    # 🔹 Get total display queue (NO LIMIT applied)
    display_queue_total = (
        StudentAppointments.objects.filter(
            Q(status="standby") | Q(status="pending"),
            is_priority="no",
            datetime__date=today
        ).count()
    )

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "queue",
        {
            "type": "send_update",
            "data": {
                "action": "queue_update",
                "stats": {
                    "non_priority_count": non_priority_count,
                    "priority_count": priority_count,
                    "display_queues": display_queue_total,  # ✅ send total
                },
            },
        },
    )



def generate_unique_survey_code():
    """ ABC-00000.generate until no duplicate """
    while True:
        letters = ''.join(random.choices(string.ascii_uppercase, k=3))
        number = random.randint(10000, 99999)  
        code = f"{letters}-{number}"
        if not Survey.objects.filter(code=code).exists():
            return code    



def generate_sequential_ticket(is_priority: str) -> str:
    """ticket number that resets daily
    P-001, R-001
    """
    today = localtime(timezone.now()).date()

    if is_priority == "yes":
        prefix = "P"
        last_ticket = StudentAppointments.objects.filter(
            is_priority="yes",
            datetime__date=today
        ).order_by("-id").first()
    else:
        prefix = "R"
        last_ticket = StudentAppointments.objects.filter(
            is_priority="no",
            datetime__date=today
        ).order_by("-id").first()

    if last_ticket and last_ticket.ticket_number:
        try:
            last_num = int(last_ticket.ticket_number.split("-")[-1])
        except ValueError:
            last_num = 0
    else:
        last_num = 0

    return f"{prefix}-{last_num + 1:03d}"



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

        course = Courses.objects.filter(id=course_id).first()
        request_type = RequestType.objects.filter(id=request_id).first()

        # Generate ticket
        new_ticket_number = generate_sequential_ticket(is_priority)

        student = StudentAppointments.objects.create(
            idNumber=id_number,
            firstName=first_name,
            middleName=middle_name,
            lastName=last_name,
            courses=course,
            requestType=request_type,
            ticket_number=new_ticket_number,
            status="pending",
            is_priority=is_priority,
            datetime=timezone.now(),
        )
        survey_code = generate_unique_survey_code()

        survey = Survey.objects.create(
                                student_appointment=student,
                                code=survey_code,
                                status="no"
                            )
        broadcast_queue_update()

        return JsonResponse({"success": True, "ticket": student.ticket_number, "survey_code": survey.code })

    return redirect("home")


def guest_submit(request):
    if request.method == "POST":
        firstName = request.POST.get("firstName")
        middleName = request.POST.get("middleName", "")
        lastName = request.POST.get("lastName")
        requestType_id = request.POST.get("request")
        is_priority = "yes" if request.POST.get("is_priority") else "no"

        try:
            requestType = RequestType.objects.get(id=requestType_id)
        except RequestType.DoesNotExist:
            return JsonResponse({"success": False, "error": "Invalid request type"})

        # Generate ticket
        new_ticket_number = generate_sequential_ticket(is_priority)

        guest = StudentAppointments.objects.create(
            firstName=firstName,
            middleName=middleName,
            lastName=lastName,
            user_type="guest",
            is_priority=is_priority,
            requestType=requestType,
            ticket_number=new_ticket_number,
            datetime=timezone.now(),
            status="pending"
        )
        survey_code = generate_unique_survey_code()

        survey = Survey.objects.create(
                                student_appointment=guest,
                                code=survey_code,
                                status="no"
                            )
        broadcast_queue_update()



        return JsonResponse({"success": True, "ticket": guest.ticket_number, "survey_code": survey.code })

    return JsonResponse({"success": False, "error": "Invalid request"})


    




