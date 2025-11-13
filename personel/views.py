# personel/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.template import loader
from .models import Appointments, Personel, Code
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import localtime
from django.db.models import Q, Case, When, Value, IntegerField
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now, timedelta





def broadcast_update():
    """Broadcast updates to BOTH groups"""
    try:
        channel_layer = get_channel_layer()
        
        # Broadcast to queue_updates group (personnel consumer)
        async_to_sync(channel_layer.group_send)(
            "queue_updates",
            {"type": "queue_update"}
        )
        
        # Broadcast to students_live_updates group (student consumer)
        async_to_sync(channel_layer.group_send)(
            "students_live_updates",
            {"type": "chat_message", "message": "personnel_action"}
        )
        
        print("✅ Update broadcasted to BOTH WebSocket groups")
    except Exception as e:
        print(f"❌ Error broadcasting update: {e}")

def broadcast_queue_update():
    """Broadcast queue updates to all connected clients"""
    try:
        channel_layer = get_channel_layer()
        
        # Broadcast to queue_updates group (personnel consumer)
        async_to_sync(channel_layer.group_send)(
            "queue_updates",
            {"type": "queue_update"}
        )
        
        # Broadcast to students_live_updates group (student consumer)  
        async_to_sync(channel_layer.group_send)(
            "students_live_updates",
            {"type": "chat_message", "message": "queue_update"}
        )
        
        print("✅ Queue update broadcasted to BOTH WebSocket groups")
    except Exception as e:
        print(f"❌ Error broadcasting queue update: {e}")

def get_or_create_personel(user):
    """Helper function to get or create a Personel record for a user"""
    try:
        return user.personel
    except Personel.DoesNotExist:
        return Personel.objects.create(user=user)

def get_next_in_line(today, next_should_be_priority):
    """Get the next student in line - includes priority when it's their turn"""
    
    print(f"🔍 DEBUG get_next_in_line: today={today}, next_should_be_priority={next_should_be_priority}")
    
    # 1. First check for standby students (highest priority)
    standby_student = Appointments.objects.filter(
        status="standby",
        datetime__date=today
    ).order_by("datetime").first()
    
    print(f"🔍 DEBUG: Standby student: {standby_student}")
    
    if standby_student:
        return standby_student
    
    # 2. Check both priority and non-priority pending students
    non_priority_pending = Appointments.objects.filter(
        status="pending",
        is_priority="no",
        datetime__date=today
    ).order_by("datetime").first()
    
    priority_pending = Appointments.objects.filter(
        status="pending", 
        is_priority="yes",
        datetime__date=today
    ).order_by("datetime").first()
    
    print(f"🔍 DEBUG: Non-priority pending: {non_priority_pending}")
    print(f"🔍 DEBUG: Priority pending: {priority_pending}")
    print(f"🔍 DEBUG: Next should be priority: {next_should_be_priority}")
    
    # If it's priority's turn AND priority student available, return priority
    if next_should_be_priority and priority_pending:
        print(f"🔍 DEBUG: Returning priority student (it's their turn)")
        return priority_pending
    
    # If non-priority available, return them
    if non_priority_pending:
        print(f"🔍 DEBUG: Returning non-priority student")
        return non_priority_pending
    
    # If no non-priority but priority available, return priority
    if priority_pending:
        print(f"🔍 DEBUG: Returning priority student (no non-priority available)")
        return priority_pending
    
    print("🔍 DEBUG: No student found in get_next_in_line")
    return None

def get_display_queue(today, limit=8):
    """
    Build the display queue with:
    - All standby students
    - Non-priority pending students (is_priority="no")
    - EXCLUDE priority pending students (is_priority="yes")
    """
    queue = []
    
    standby_students = list(
        Appointments.objects.filter(
            status="standby",
            datetime__date=today
        ).order_by("datetime")
    )
    queue.extend(standby_students)
    
    if len(queue) >= limit:
        return queue[:limit]
    
    non_priority_students = list(
        Appointments.objects.filter(
            status="pending",
            is_priority="no",
            datetime__date=today
        ).order_by("datetime")
    )
    
    for student in non_priority_students:
        if len(queue) >= limit:
            break
        queue.append(student)
    
    return queue[:limit]

@login_required
def home(request):
    print("🔍 PERSONNEL VIEW: Current user:", request.user)
    
    # Use timezone-aware now for Philippines time - CONSISTENT DATE HANDLING
    now_ph = localtime(timezone.now())
    today = now_ph.date()
    
    print(f"🔍 PERSONNEL VIEW DEBUG:")
    print(f"   - Today's date: {today}")
    print(f"   - Current time: {now_ph}")
    
    # Auto-cancel expired skips
    expired = Appointments.objects.filter(
        status="skip", 
        skip_until__lt=now_ph
    )
    print(f"   - Expired skips: {expired.count()}")
    
    for appt in expired:
        appt.status = "cancel"
        appt.save()

    # DEBUG: Check current student with same query as consumer
    get_current_number = Appointments.objects.filter(
        status="current",
        datetime__date=today 
    ).order_by("datetime").first()
    
    print(f"🔍 PERSONNEL VIEW - Current student query result: {get_current_number}")
    if get_current_number:
        print(f"🔍 PERSONNEL VIEW - Current student details: {get_current_number.ticket_number}, {get_current_number.status}, Date: {get_current_number.datetime.date() if get_current_number.datetime else 'No date'}")
    else:
        print(f"🔍 PERSONNEL VIEW - No current student found for date: {today}")
        # Debug all students
        all_students = Appointments.objects.filter(datetime__date=today)
        print(f"🔍 PERSONNEL VIEW - All students today: {all_students.count()}")
        for s in all_students:
            print(f"     - {s.ticket_number}: {s.status}")

    # Calculate served count for priority logic
    served_today = Appointments.objects.filter(
        status__in=["done", "current"],
        datetime__date=today
    ).count()

    next_should_be_priority = (served_today % 3) == 2

    if request.method == "POST":
        if 'start' in request.POST:
            print(f"🔍 PERSONNEL VIEW: Start Serving button clicked")
            print(f"🔍 PERSONNEL VIEW: Served today: {served_today}, Next should be priority: {next_should_be_priority}")

            next_student = get_next_in_line(today, next_should_be_priority)
            
            print(f"🔍 PERSONNEL VIEW: Next student to start: {next_student}")
            
            if next_student:
                next_student.status = "current"
                next_student.save()
                print(f"🔍 PERSONNEL VIEW: Started serving: {next_student.ticket_number} (Priority: {next_student.is_priority})")
                broadcast_update()
                broadcast_queue_update()
            else:
                print("🔍 PERSONNEL VIEW: No next student found to start serving")
                messages.error(request, "No students in queue to serve.")
            
            return redirect("personel")
        
        broadcast_update()
        broadcast_queue_update()
        return redirect("personel")

    survey_today = now().date()
    since = survey_today - timedelta(days=1)
    display_queues = get_display_queue(today, limit=8)
    display_survey = Code.objects.filter(
        status="used",
        created_at__date__gte=since
    ).order_by("-created_at")

    print(f"🔍 PERSONNEL VIEW - Display queues count: {len(display_queues)}")
    print(f"🔍 PERSONNEL VIEW - Survey count: {display_survey.count()}")

    template = loader.get_template('personel/home.html')
    context = {
        'non_priority_students': Appointments.objects.filter(
            is_priority="no",
            status="pending",
            datetime__date=today 
        ).order_by("datetime"),
        'priority_students': Appointments.objects.filter(
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
        ).order_by("status_order", "datetime"),
        'get_first_pending_non_priority': Appointments.objects.filter(
            is_priority="no",
            status="pending",
            datetime__date=today 
        ).order_by("datetime").first(),
        'get_current_number': get_current_number,
        'skip_non_priority_students': Appointments.objects.filter(
            is_priority="no",
            status="skip",
            datetime__date=today 
        ).order_by("datetime"),
        'next_in_line': get_next_in_line(today, next_should_be_priority),
        'display_queues': display_queues,
        'next_should_be_priority': next_should_be_priority,
        'get_first_non_priority_students': Appointments.objects.filter(
            is_priority="no",
            status="pending",
            datetime__date=today 
        ).order_by("datetime").first(),
        'display_survey': display_survey,
    }
    return HttpResponse(template.render(context, request))

@login_required
def done_current_number(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        ticket_id = request.POST.get('ticket_number')

        current_number = get_object_or_404(Appointments, id=ticket_id)
        
        today = timezone.now().date()
        now_ph = localtime(timezone.now())

        if current_number:
            # Get or create Personel for the current user
            personel = get_or_create_personel(request.user)
            
            if action == 'done':
                current_number.status = 'done'
                current_number.skip_until = None
                current_number.skip_count = 0
                current_number.served_by = personel
                current_number.save()
                broadcast_update()
                broadcast_queue_update()
            elif action == 'skip':
                if current_number.is_priority == 'yes':
                    current_number.status = 'skip'
                    current_number.served_by = personel
                    current_number.save()
                    broadcast_update()
                    broadcast_queue_update()
                else:
                    current_number.served_by = personel
                    current_number.handle_skip() 
                    broadcast_update()
                    broadcast_queue_update()

            today = timezone.now().date()

            served_today = Appointments.objects.filter(
                status__in=["done", "current"],
                datetime__date=today
            ).count()

            next_should_be_priority = (served_today % 3) == 2

            next_student = get_next_in_line(today, next_should_be_priority)
            
            if next_student:
                next_student.status = "current"
                next_student.save()
                broadcast_update()
                broadcast_queue_update()
                print(f"Set next student as current: {next_student.ticket_number} (Priority: {next_student.is_priority})")
            else:
                print("No next student found")
                
        return redirect('personel')
    return redirect('personel')

@login_required
def standby(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        ticket_id = request.POST.get('ticket_number') 

        current_number = get_object_or_404(Appointments, id=ticket_id)

        if current_number:
            if action == 'standby':
                current_number.status = 'standby'
                current_number.save()
                broadcast_update()
                broadcast_queue_update()
        return redirect('personel')

@login_required
def priority_standby(request):
    if request.method == "POST":
        ticket_id = request.POST.get("ticket_number")  
        action = request.POST.get("action")  

        student = get_object_or_404(Appointments, id=ticket_id)

        if action == "standby":
            student.status = "standby"
            student.save()
            broadcast_update()
            broadcast_queue_update()

    return redirect("personel")

@login_required
def end_all_appointments(request):
    if request.method == "POST":
        today = timezone.now().date()
        now_ph = localtime(timezone.now())
        
        Appointments.objects.filter(
            status__in=["pending", "skip", "current"]
        ).update(status="cancel")
        
        broadcast_update()
        broadcast_queue_update()
        return redirect("personel")  
    return redirect("personel")

@login_required
def queue_data_api(request):
    """API endpoint to get current queue data for next 3 students"""
    try:
        today = timezone.now().date()
        
        display_queues = get_display_queue(today, limit=3)
        
        queue_list = []
        for queue in display_queues:
            queue_list.append({
                'ticket_number': queue.ticket_number,
            })
        
        print(f"API returning {len(queue_list)} queue items")
        return JsonResponse(queue_list, safe=False)
    except Exception as e:
        print(f"Error in queue_data_api: {e}")
        return JsonResponse([], safe=False)

@login_required
def debug_all_students(request):
    """Debug view to see all students"""
    today = timezone.now().date()
    students = Appointments.objects.filter(datetime__date=today).order_by('status', 'datetime')
    
    result = []
    for s in students:
        result.append({
            'ticket': s.ticket_number,
            'status': s.status,
            'priority': s.is_priority,
            'name': f"{s.firstName} {s.lastName}",
            'datetime': s.datetime.strftime("%H:%M") if s.datetime else None
        })
    
    return JsonResponse({'students': result})

def login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user) 
            messages.success(request, "Login successful.")
            return redirect("personel")  
        else:
            messages.error(request, "Invalid username or password.")
            return redirect("auth_login")

    template = loader.get_template('personel/auth/login.html')
    context = {}
    return HttpResponse(template.render(context, request))

def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        if not username or not password:
            messages.error(request, "Username and password are required.")
            return redirect("auth_register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("auth_register")

        user = User.objects.create_user(username=username, password=password)
        
        Personel.objects.create(user=user)

        messages.success(request, "Account created! You can now log in.")
        return redirect("auth_login")

    return render(request, "personel/auth/register.html")

def logout(request):
    auth_logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("auth_login")

def new_home(request):
    template = loader.get_template("personel/new_home.html")
    context = {}
    return HttpResponse(template.render(context, request))


