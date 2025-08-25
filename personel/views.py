from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import loader
from .models import StudentAppointments
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import localtime
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Q, Case, When, Value, IntegerField

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def broadcast_update():
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "students_live_updates",   # must match consumer group_name
        {"type": "chat_message", "message": "update"}
    )

def get_next_in_line(today, next_should_be_priority):
    """Get the next student in line based on priority pattern with standby insertion"""
    
    # First check for any standby students (they take highest priority and cut in line)
    standby_student = StudentAppointments.objects.filter(
        status="standby",
        datetime__date=today
    ).order_by("datetime").first()
    
    if standby_student:
        return standby_student
    
    # If no standby, follow the priority pattern using the provided parameter
    # REMOVE THIS BLOCK - don't recalculate served_today and next_should_be_priority
    # served_today = StudentAppointments.objects.filter(
    #     status__in=["done", "current"],
    #     datetime__date=today
    # ).count()
    # next_should_be_priority = (served_today % 3) == 2
    
    if next_should_be_priority:
        # Try priority pending students first
        priority_pending = StudentAppointments.objects.filter(
            status="pending",
            is_priority="yes",
            datetime__date=today
        ).order_by("datetime").first()
        
        if priority_pending:
            return priority_pending
        
        # Fallback to regular pending if no priority available
        regular_pending = StudentAppointments.objects.filter(
            status="pending",
            is_priority="no",
            datetime__date=today
        ).order_by("datetime").first()
        
        if regular_pending:
            return regular_pending
        
    else:
        # Try regular pending students first
        regular_pending = StudentAppointments.objects.filter(
            status="pending",
            is_priority="no",
            datetime__date=today
        ).order_by("datetime").first()
        
        if regular_pending:
            return regular_pending
        
        # Fallback to priority pending if no regular available
        priority_pending = StudentAppointments.objects.filter(
            status="pending",
            is_priority="yes",
            datetime__date=today
        ).order_by("datetime").first()
        
        if priority_pending:
            return priority_pending
    
    return None

def get_display_queue(today, limit=5):
    """
    Build the display queue by simulating get_next_in_line multiple times
    """
    queue = []
    
    # Make a copy of the current state to simulate without affecting the database
    served_today = StudentAppointments.objects.filter(
        status__in=["done", "current"],
        datetime__date=today
    ).count()
    
    # Simulate the next 'limit' students that would be chosen
    for i in range(limit):
        # Calculate what the pattern would be for the next student
        next_should_be_priority = ((served_today + i) % 3) == 2
        
        # Simulate get_next_in_line logic
        # First check for standby
        standby_student = StudentAppointments.objects.filter(
            status="standby",
            datetime__date=today
        ).exclude(id__in=[s.id for s in queue]).order_by("datetime").first()
        
        if standby_student:
            queue.append(standby_student)
            continue
            
        # Then follow priority pattern
        if next_should_be_priority:
            priority_pending = StudentAppointments.objects.filter(
                status="pending",
                is_priority="yes",
                datetime__date=today
            ).exclude(id__in=[s.id for s in queue]).order_by("datetime").first()
            
            if priority_pending:
                queue.append(priority_pending)
                continue
                
            # Fallback to regular
            regular_pending = StudentAppointments.objects.filter(
                status="pending",
                is_priority="no",
                datetime__date=today
            ).exclude(id__in=[s.id for s in queue]).order_by("datetime").first()
            
            if regular_pending:
                queue.append(regular_pending)
                continue
                
        else:
            regular_pending = StudentAppointments.objects.filter(
                status="pending",
                is_priority="no",
                datetime__date=today
            ).exclude(id__in=[s.id for s in queue]).order_by("datetime").first()
            
            if regular_pending:
                queue.append(regular_pending)
                continue
                
            # Fallback to priority
            priority_pending = StudentAppointments.objects.filter(
                status="pending",
                is_priority="yes",
                datetime__date=today
            ).exclude(id__in=[s.id for s in queue]).order_by("datetime").first()
            
            if priority_pending:
                queue.append(priority_pending)
                continue
    
    return queue

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
            else:
                print("No students available to start")
            
            return redirect("personel")
        
        broadcast_update()
        return redirect("personel")
                                                           
    template = loader.get_template('personel/home.html')
    context = {
        'non_priority_students': non_priority_students,
        'priority_students': priority_students,
        'get_first_pending_non_priority': get_first_pending_non_priority,
        'get_current_number': get_current_number,
        'skip_non_priority_students': skip_non_priority_students,
        'next_in_line': next_in_line,
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
            status__in=["pending", "skip", "current",]
        ).update(status="cancel")
        
        broadcast_update()
        return redirect("personel")  
    return redirect("personel")


def test(request):
    template = loader.get_template('personel/test.html')
    context = {}

    return HttpResponse(template.render(context, request))