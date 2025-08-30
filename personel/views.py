from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import loader
from .models import StudentAppointments, Personel
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import localtime
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Q, Case, When, Value, IntegerField
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def broadcast_update():
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "students_live_updates",   # must match consumer group_name
        {"type": "chat_message", "message": "update"}
    )

def get_next_in_line(today, next_should_be_priority):
    """Get the next student in line - EXCLUDE priority pending students"""
    
    # First check for any standby students (they take highest priority and cut in line)
    standby_student = StudentAppointments.objects.filter(
        status="standby",
        datetime__date=today
    ).order_by("datetime").first()
    
    if standby_student:
        return standby_student
    
    # If no standby, ONLY consider non-priority students (exclude priority pending)
    # Regardless of the pattern, we only pick from non-priority students
    
    non_priority_pending = StudentAppointments.objects.filter(
        status="pending",
        is_priority="no",  # Only non-priority
        datetime__date=today
    ).order_by("datetime").first()
    
    if non_priority_pending:
        return non_priority_pending
    
    # If no non-priority students available, return None
    # (We're excluding priority pending students completely)
    return None

def get_display_queue(today, limit=8):
    """
    Build the display queue with:
    - All standby students
    - Non-priority pending students (is_priority="no")
    - EXCLUDE priority pending students (is_priority="yes")
    """
    queue = []
    
    # 1) Add all standby students first (they cut in line)
    standby_students = list(
        StudentAppointments.objects.filter(
            status="standby",
            datetime__date=today
        ).order_by("datetime")
    )
    queue.extend(standby_students)
    
    # If we already have enough standby students, return them
    if len(queue) >= limit:
        return queue[:limit]
    
    # 2) Add non-priority pending students only (exclude priority pending)
    non_priority_students = list(
        StudentAppointments.objects.filter(
            status="pending",
            is_priority="no",  # Only non-priority
            datetime__date=today
        ).order_by("datetime")
    )
    
    # Add non-priority students until we reach the limit
    for student in non_priority_students:
        if len(queue) >= limit:
            break
        queue.append(student)
    
    return queue[:limit]


def home(request):
    today = timezone.now().date()
    now_ph = localtime(timezone.now())
    
    # Auto-cancel expired skips
    expired = StudentAppointments.objects.filter(
        status="skip", skip_until__lt=now_ph
    )
    for appt in expired:
        appt.status = "cancel"
        appt.save()

    today = now_ph.date() 

    # pending non priority students
    non_priority_students = StudentAppointments.objects.filter(
        is_priority="no",
        status="pending",
        datetime__date=today 
    ).order_by("datetime") 

    get_non_priority_students = StudentAppointments.objects.filter(
        is_priority="no",
        status="pending",
        datetime__date=today 
    ).order_by("datetime").first() 

    # skip non priority students
    skip_non_priority_students = StudentAppointments.objects.filter(
        is_priority="no",
        status="skip",
        datetime__date=today 
    ).order_by("datetime") 

    # get stand by students
    get_standby_students = StudentAppointments.objects.filter(
        status="standby",
        datetime__date=today 
    ).order_by("datetime").first()

    # pending priority students
    priority_students = StudentAppointments.objects.filter(
        is_priority="yes",
        status__in=["pending", "skip"],
        datetime__date=today 
    ).annotate(
        status_order=Case(
            When(status="pending", then=Value(1)),
            When(status="skip", then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
    ).order_by("status_order", "datetime")  

    # get the first pending non-priority student
    get_first_pending_non_priority = StudentAppointments.objects.filter(
        is_priority="no",
        status="pending",
        datetime__date=today 
    ).order_by("datetime").first() 

    # get the current student
    get_current_number = StudentAppointments.objects.filter(
        status="current",
        datetime__date=today 
    ).order_by("datetime").first()

    served_today = StudentAppointments.objects.filter(
        status__in=["done", "current"],
        datetime__date=today
    ).count()

    next_should_be_priority = (served_today % 3) == 2
    
    # Use the helper function to get next in line
    next_in_line = get_next_in_line(today, next_should_be_priority)

    if request.method == "POST":
        if 'start' in request.POST:
            served_count = StudentAppointments.objects.filter(
                status__in=["done", "current"],
                datetime__date=today
            ).count()
            
            next_should_be_priority = (served_count % 3) == 2

            # Use the same helper function to get next student
            next_student = get_next_in_line(today, next_should_be_priority)
            
            if next_student:
                next_student.status = "current"
                next_student.save()
                broadcast_update()
                print(f"Started: {next_student.ticket_number} (Priority: {next_student.is_priority})")            
            
            
            return redirect("personel")
        
        broadcast_update()
        return redirect("personel")

    display_queues  = get_display_queue(today, limit=8)

    template = loader.get_template('personel/home.html')
    context = {
        'non_priority_students': non_priority_students,
        'priority_students': priority_students,
        'get_first_pending_non_priority': get_first_pending_non_priority,
        'get_current_number': get_current_number,
        'skip_non_priority_students': skip_non_priority_students,
        'next_in_line': next_in_line,
        'display_queues' : display_queues ,
        'next_should_be_priority': next_should_be_priority,
        'get_first_non_priority_students': get_non_priority_students,
    }
    return HttpResponse(template.render(context, request))

def done_current_number(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        ticket_id = request.POST.get('ticket_number')

        current_number = get_object_or_404(StudentAppointments, id=ticket_id)
        
        today = timezone.now().date()
        now_ph = localtime(timezone.now())

        if current_number:
            if action == 'done':
                current_number.status = 'done'
                current_number.skip_until = None
                current_number.skip_count = 0
                current_number.save()
                broadcast_update()
            elif action == 'skip':
                if current_number.is_priority == 'yes':
                    current_number.status = 'skip'
                    current_number.save()
                    broadcast_update()
                else:
                   current_number.skip_count += 1
                   if current_number.skip_count >= 3:
                        current_number.status = 'cancel'
                        current_number.skip_until = None
                   elif current_number.skip_count == 1:
                        current_number.status = 'skip'
                        current_number.skip_until = timezone.now() + timedelta(hours=1)
                   else:
                        current_number.status = 'skip'
                   current_number.save()  
                   broadcast_update()  

            # Get count of served students today to determine pattern
            served_today = StudentAppointments.objects.filter(
                status__in=["done", "current"],
                datetime__date=today
            ).count()

            next_should_be_priority = (served_today % 3) == 2

            # Use the helper function to get next student
            next_student = get_next_in_line(today, next_should_be_priority)
            
            # If we found a next student, set them as current
            if next_student:
                next_student.status = "current"
                next_student.save()
                broadcast_update()
                print(f"Set next student as current: {next_student.ticket_number} (Priority: {next_student.is_priority})")
            else:
                print("No next student found")
                
        return redirect('personel')
    return redirect('personel')

def standby(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        ticket_id = request.POST.get('ticket_number')  # get ID from form

        current_number = get_object_or_404(StudentAppointments, id=ticket_id)

        if current_number:
            if action == 'standby':
                current_number.status = 'standby'
                current_number.save()
                broadcast_update()
        return redirect('personel')
    



def priority_standby(request):
    if request.method == "POST":
        ticket_id = request.POST.get("ticket_number")  
        action = request.POST.get("action")  

        student = get_object_or_404(StudentAppointments, id=ticket_id)

        if action == "standby":
            student.status = "standby"
            student.save()
            broadcast_update()

    return redirect("personel")  



def end_all_appointments(request):
    if request.method == "POST":
        # Get today's date
        today = timezone.now().date()
        now_ph = localtime(timezone.now())
        
        # Cancel only today's pending and skip appointments
        StudentAppointments.objects.filter(
            datetime__date=now_ph,
            status__in=["pending", "skip", "current",'done', 'cancel']
        ).update(status="pending")
        
        broadcast_update()
        return redirect("personel")  
    return redirect("personel")


def login(request):

        
    template = loader.get_template('personel/auth/login.html')
    context = {
    }
    return HttpResponse(template.render(context, request))


def register(request):
   

    template = loader.get_template('personel/auth/register.html')
    context = {
    }
    return HttpResponse(template.render(context, request))


def logout(request):
    request.session.flush()  # clears all session data
    messages.success(request, "Logged out successfully.")
    return redirect("auth_login")
