from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import loader
from .models import StudentAppointments
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import localtime
from django.shortcuts import redirect, get_object_or_404


from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def broadcast_update():
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "students_live_updates",   # must match consumer group_name
        {"type": "chat_message", "message": "update"}
    )




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
    # print(get_skip_non_priority_students.ticket_number)

    

    # pending priority students
    priority_students = StudentAppointments.objects.filter(
        is_priority="yes",
        status="pending",
        datetime__date=today 
    ).order_by("datetime")  

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


    next_in_line = None
    # 1. First check for PRIORITY standby
    priority_standby = StudentAppointments.objects.filter(
        status="standby",
        is_priority="yes",
        datetime__date=today
    ).order_by("datetime").first()
    
    # 2. Then check for REGULAR standby
    regular_standby = StudentAppointments.objects.filter(
        status="standby",
        is_priority="no",
        datetime__date=today
    ).order_by("datetime").first()

    # 3. Then check for PRIORITY pending
    priority_pending = StudentAppointments.objects.filter(
        is_priority="yes",
        status="pending",
        datetime__date=today
    ).order_by("datetime").first()

     # 4. Finally check for REGULAR pending
    regular_pending = StudentAppointments.objects.filter(
        is_priority="no",
        status="pending",
        datetime__date=today
    ).order_by("datetime").first()

    # Determine next in line based on priority order
    if priority_standby:
        next_in_line = priority_standby
        
        
    elif regular_standby:
        next_in_line = regular_standby
    elif priority_pending:
        next_in_line = priority_pending
    elif regular_pending:
        next_in_line = regular_pending

    if request.method == "POST":
        if 'start' in request.POST:
            # FIRST: Check for PRIORITY standby students
            priority_standby = StudentAppointments.objects.filter(
                status="standby",
                is_priority="yes",  
                datetime__date=today
            ).order_by("datetime").first()

            # SECOND: Check for REGULAR standby students
            regular_standby = StudentAppointments.objects.filter(
                status="standby",
                is_priority="no",   
                datetime__date=today
            ).order_by("datetime").first()

            # THIRD: Check for pending students
            next_pending = StudentAppointments.objects.filter(
                is_priority="no",
                status="pending",
                datetime__date=today
            ).order_by("datetime").first()

            # Process in priority order
            if priority_standby:
                priority_standby.status = "current"
                priority_standby.save()
                broadcast_update()
                print(f"Started priority standby: {priority_standby.ticket_number}")
            elif regular_standby:
                regular_standby.status = "current"
                regular_standby.save()
                broadcast_update()
                print(f"Started regular standby: {regular_standby.ticket_number}")
            elif next_pending:
                next_pending.status = "current"
                next_pending.save()
                broadcast_update()
                print(f"Started pending: {next_pending.ticket_number}")
            else:
                print("No students available to start")
            
            return redirect("personel")
        
        broadcast_update()
        return redirect("personel")
                                                           
    template = loader.get_template('personel/home.html')
    context = {
        'non_priority_students': non_priority_students,
        'priority_students': priority_students,
        'get_first_pending_non_priority' : get_first_pending_non_priority,
        'get_current_number': get_current_number,
        'skip_non_priority_students' :skip_non_priority_students,
        'next_in_line' : next_in_line,
        'get_first_non_priority_students' : get_non_priority_students,
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
                current_number.skip_count = "0"
                current_number.save()
                broadcast_update()
            elif action == 'skip':
                if current_number.is_priority == 'yes':
                    current_number.status ='pending'
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

            # Determine next in line using the correct priority order:
            # 1. Priority Standby → 2. Regular Standby → 3. Priority Pending → 4. Regular Pending
            
            priority_standby = StudentAppointments.objects.filter(
                status="standby",
                is_priority="yes",
                datetime__date=now_ph
            ).order_by("datetime").first()

            regular_standby = StudentAppointments.objects.filter(
                status="standby",
                is_priority="no",
                datetime__date=now_ph
            ).order_by("datetime").first()

            priority_pending = StudentAppointments.objects.filter(
                is_priority="yes",
                status="pending",
                datetime__date=now_ph
            ).order_by("datetime").first()

            regular_pending = StudentAppointments.objects.filter(
                is_priority="no",
                status="pending",
                datetime__date=now_ph
            ).order_by("datetime").first()
            
            # Set next current number in priority order
            next_student = None
            if priority_standby:
                next_student = priority_standby
            elif regular_standby:
                next_student = regular_standby
            elif priority_pending:
                next_student = priority_pending
            elif regular_pending:
                next_student = regular_pending
            
            # If we found a next student, set them as current
            if next_student:
                next_student.status = "current"
                next_student.save()
                broadcast_update()
                
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