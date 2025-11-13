# students/views.py
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import loader
from personel.models import Appointments, RequestType, Courses, Code
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import localtime
from django.http import JsonResponse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import random, string




def broadcast_queue_update():
    """Broadcast queue updates to all connected clients with CONSISTENT date handling"""
    now_ph = localtime(timezone.now())
    today = now_ph.date()

    try:
        channel_layer = get_channel_layer()
        
        print("🔄 Broadcasting queue update to ALL groups...")
        
        # Send to queue_updates group (for personnel consumer)
        async_to_sync(channel_layer.group_send)(
            "queue_updates",
            {
                "type": "queue_update",  # This will trigger queue_update method in personnel consumer
            },
        )
        
        # Send to students_live_updates group (for student consumer AND personnel consumer)
        async_to_sync(channel_layer.group_send)(
            "students_live_updates",
            {
                "type": "chat_message",  # This will trigger chat_message method in both consumers
                "message": "student_submission"  # More specific message type
            },
        )
        
        print("✅ Student submission broadcasted to BOTH WebSocket groups")

    except Exception as e:
        print(f"❌ Error broadcasting update: {e}")

def generate_unique_survey_code():
    while True:
        letters = ''.join(random.choices(string.ascii_uppercase, k=2))
        number = random.randint(100, 9999)  
        code = f"{letters}-{number}"
        if not Code.objects.filter(code=code).exists():
            return code    

def generate_sequential_ticket(is_priority: str) -> str:
    """ticket number that resets daily
    P-001, R-001
    """
    today = localtime(timezone.now()).date()

    if is_priority == "yes":
        prefix = "P"
        last_ticket = Appointments.objects.filter(
            is_priority="yes",
            datetime__date=today
        ).order_by("-id").first()
    else:
        prefix = "R"
        last_ticket = Appointments.objects.filter(
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

    template = loader.get_template('students/home.html')
    context = {
        'courses': courses,
        'requests': requests,
    }
    return HttpResponse(template.render(context, request))

def student_submit(request):
    if request.method == "POST":
        first_name = request.POST.get("firstName")
        last_name = request.POST.get("lastName")
        course_id = request.POST.get("course")
        request_id = request.POST.get("request")
        custom_request = request.POST.get("custom_request")
        is_priority = "yes" if request.POST.get("is_priority") else "no"

        course = Courses.objects.filter(id=course_id).first()
         # Handle "Other" request type
        if request_id == "other":
            request_type = None
        else:
            request_type = RequestType.objects.filter(id=request_id).first()

        # Generate ticket
        new_ticket_number = generate_sequential_ticket(is_priority)

        student = Appointments.objects.create(
            firstName=first_name,
            lastName=last_name,
            courses=course,
            requestType=request_type,
            custom_request=custom_request,
            ticket_number=new_ticket_number,
            status="pending",
            is_priority=is_priority,
            datetime=timezone.now(),
        )
        survey_code = generate_unique_survey_code()

        survey = Code.objects.create(
            appointments = student,
            code=survey_code,
        )
        
        print(f"🎓 New student created: {student.ticket_number} (Priority: {is_priority})")
        broadcast_queue_update()

        return JsonResponse({"success": True, "ticket": student.ticket_number, "survey_code": survey.code })

    return redirect("home")

def guest_submit(request):
    if request.method == "POST":
        firstName = request.POST.get("firstName")
        lastName = request.POST.get("lastName")
        requestType_id = request.POST.get("request")
        is_priority = "yes" if request.POST.get("is_priority") else "no"

        try:
            requestType = RequestType.objects.get(id=requestType_id)
        except RequestType.DoesNotExist:
            return JsonResponse({"success": False, "error": "Invalid request type"})

        # Generate ticket
        new_ticket_number = generate_sequential_ticket(is_priority)

        guest = Appointments.objects.create(
            firstName=firstName,
            lastName=lastName,
            user_type="guest",
            is_priority=is_priority,
            requestType=requestType,
            ticket_number=new_ticket_number,
            datetime=timezone.now(),
            status="pending"
        )
        survey_code = generate_unique_survey_code()

        survey = Code.objects.create(
            appointments = guest,         
            code=survey_code,
        )
        
        print(f"🎓 New guest created: {guest.ticket_number} (Priority: {is_priority})")
        broadcast_queue_update()

        return JsonResponse({"success": True, "ticket": guest.ticket_number, "survey_code": survey.code })

    return JsonResponse({"success": False, "error": "Invalid request"})

def form(request):
    courses = Courses.objects.all()
    requests = RequestType.objects.all()
    template = loader.get_template('students/form.html')
    context = {
        'courses' : courses,
        'requests' : requests,
    }

    return HttpResponse(template.render(context, request))