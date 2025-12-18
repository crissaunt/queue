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


from .models import QueueControl


def is_queue_running():
    qc = QueueControl.get_queue_control()
    return qc.is_running


def check_authentication(user):
    return user.is_authenticated

# In personel/views.py
def toggle_queue(request):
    if request.method == "POST":
        qc = QueueControl.get_queue_control()
        qc.is_running = not qc.is_running
        qc.save()

        status = "started" if qc.is_running else "stopped"
        messages.success(request, f"Queue has been {status}.")
        
        # Broadcast update to ALL connected clients (personnel AND display)
        broadcast_update()
        broadcast_queue_update()

    return redirect("personel")

# In personel/views.py - update broadcast functions
def broadcast_update():
    """Broadcast updates to BOTH groups"""
    try:
        channel_layer = get_channel_layer()
        
        # Broadcast to queue_updates group (personnel consumer)
        async_to_sync(channel_layer.group_send)(
            "queue_updates",
            {"type": "queue_update"}
        )
        
        # Broadcast to students_live_updates group (student consumer AND display)
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
        
        # Broadcast to students_live_updates group (student consumer AND display)  
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
    
    # 1. First check for standby students (highest priority) - BOTH priority and non-priority
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
    - ALL standby students (both priority and non-priority)
    - ONLY non-priority pending students
    - Priority pending students NEVER appear in Next Queue
    """
    queue = []
    
    # 1. First get ALL standby students (highest priority)
    standby_students = list(
        Appointments.objects.filter(
            status="standby",
            datetime__date=today
        ).order_by("datetime")
    )
    queue.extend(standby_students)
    
    if len(queue) >= limit:
        return queue[:limit]
    
    # 2. Then get ONLY non-priority pending students
    # Priority pending students are EXCLUDED from Next Queue
    non_priority_pending_students = list(
        Appointments.objects.filter(
            status="pending",
            is_priority="no",
            datetime__date=today
        ).order_by("datetime")
    )
    
    for student in non_priority_pending_students:
        if len(queue) >= limit:
            break
        queue.append(student)
    
    return queue[:limit]


def get_full_queue(today):
    return Appointments.objects.filter(
        datetime__date=today
    ).exclude(status__in=["done", "cancel"]) \
     .order_by("datetime")


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

    # DEBUG: Check current student
    get_current_number = Appointments.objects.filter(
        status="current",
        datetime__date=today 
    ).order_by("datetime").first()
    
    print(f"🔍 PERSONNEL VIEW - Current student query result: {get_current_number}")

    if request.method == "POST":
        if 'start' in request.POST:
            print(f"🔍 PERSONNEL VIEW: Start Serving button clicked")

            if not is_queue_running():
                print("🔍 PERSONNEL VIEW: Queue is stopped, auto-starting queue...")
                qc = QueueControl.get_queue_control()
                qc.is_running = True
                qc.save()
                broadcast_queue_update()
                messages.info(request, "Queue has been automatically started.")

            # Only move to next if queue is running
            next_student = get_next_in_line(today, False)  # No rotation needed
            print(f"🔍 PERSONNEL VIEW: Next student to start: {next_student}")
            
            if next_student:
                next_student.status = "current"
                next_student.save()
                print(f"🔍 PERSONNEL VIEW: Started serving: {next_student.ticket_number}")
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

    template = loader.get_template('personel/home.html')
    context = {
        'queue_state': is_queue_running(),
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
        'next_in_line': get_next_in_line(today, False),  # No rotation
        'display_queues': display_queues,
        'display_survey': display_survey,
        'full_queue': get_full_queue(today),
    }
    return HttpResponse(template.render(context, request))


def done_current_number(request):
    if request.method == 'POST':
        # Check if queue is active
        if not is_queue_running():
            messages.error(request, "Queue is currently stopped. Cannot process actions.")
            return redirect('personel')
            
        action = request.POST.get('action')
        ticket_id = request.POST.get('ticket_number')

        # Validate ticket_id
        if not ticket_id or ticket_id.strip() == '':
            messages.error(request, "Invalid student ID. Please try again.")
            return redirect('personel')
        
        try:
            # Ensure ticket_id can be converted to integer
            ticket_id = int(ticket_id)
            current_number = get_object_or_404(Appointments, id=ticket_id)
        except (ValueError, TypeError):
            messages.error(request, "Invalid student ID format.")
            return redirect('personel')
        except Appointments.DoesNotExist:
            messages.error(request, "Student not found.")
            return redirect('personel')

        if current_number:
            # Get or create Personel for the current user
            personel = get_or_create_personel(request.user)
            
            if action == 'done':
                current_number.status = 'done'
                current_number.skip_until = None
                current_number.skip_count = 0
                current_number.served_by = personel
                current_number.save()
                
                # UPDATE THE CODE STATUS TO 'used' WHEN APPOINTMENT IS DONE
                try:
                    code_obj = Code.objects.get(appointments=current_number)
                    code_obj.status = 'pending'
                    code_obj.save()
                    print(f"✅ Updated code {code_obj.code} status to 'used'")
                except Code.DoesNotExist:
                    print(f"⚠️ No code found for appointment {current_number.id}")
                except Code.MultipleObjectsReturned:
                    # If there are multiple codes, update all of them
                    code_objs = Code.objects.filter(appointments=current_number)
                    code_objs.update(status='used')
                    print(f"✅ Updated {code_objs.count()} codes to 'used'")
                
                broadcast_update()
                broadcast_queue_update()
                
                messages.success(request, f"Student {current_number.ticket_number} marked as done.")
                broadcast_update()
                broadcast_queue_update()
                
                messages.success(request, f"Student {current_number.ticket_number} marked as done.")
                
            elif action == 'skip':
                print(f"🔍 SKIP ACTION DEBUG:")
                print(f"   - Student: {current_number.ticket_number}")
                print(f"   - Priority: {current_number.is_priority}")
                print(f"   - Status before: {current_number.status}")
                
                # Mark as served by
                current_number.served_by = personel
                
                # Handle skip based on priority
                if current_number.is_priority == 'yes':
                    print(f"   - Priority student skip logic")
                    current_number.status = 'skip'
                    current_number.save()
                else:
                    print(f"   - Non-priority student skip logic")
                    # Check if handle_skip method exists
                    if hasattr(current_number, 'handle_skip'):
                        current_number.handle_skip()
                    else:
                        # Fallback: simple skip
                        current_number.status = 'skip'
                        current_number.save()
                
                print(f"   - Status after: {current_number.status}")
                
                broadcast_update()
                broadcast_queue_update()
                messages.info(request, f"Student {current_number.ticket_number} skipped.")

            today = timezone.now().date()

            # ALWAYS get next student if queue is running
            if is_queue_running():
                next_student = get_next_in_line(today, False)  # No rotation
                
                if next_student:
                    next_student.status = "current"
                    next_student.save()
                    broadcast_update()
                    broadcast_queue_update()
                    print(f"Set next student as current: {next_student.ticket_number}")
                else:
                    print("No next student found")
                    
        return redirect('personel')
    return redirect('personel')

def standby(request):
    if request.method == 'POST':
        if not is_queue_running():
            messages.error(request, "Queue is currently stopped. Cannot process actions.")
            return redirect('personel')
            
        action = request.POST.get('action')
        ticket_id = request.POST.get('ticket_number')
        
        # Check if ticket_id is empty
        if not ticket_id or ticket_id.strip() == '':
            messages.error(request, "Invalid student ID. Please try again.")
            return redirect('personel')
            
        try:
            # Convert to integer
            ticket_id = int(ticket_id)
            current_number = get_object_or_404(Appointments, id=ticket_id)

            if current_number:
                if action == 'standby':
                    current_number.status = 'standby'
                    current_number.save()
                    
                    broadcast_update()
                    broadcast_queue_update()
                    messages.info(request, f"Student {current_number.ticket_number} moved to standby.")
                    
        except (ValueError, TypeError):
            messages.error(request, "Invalid student ID format.")
        except Appointments.DoesNotExist:
            messages.error(request, "Student not found.")
            
        return redirect('personel')


def priority_standby(request):
    if request.method == "POST":
        if not is_queue_running():
            messages.error(request, "Queue is currently stopped. Cannot process actions.")
            return redirect("personel")
            
        ticket_id = request.POST.get("ticket_number")  
        action = request.POST.get("action")  
        
        # Validate ticket_id
        if not ticket_id or ticket_id.strip() == '':
            messages.error(request, "Invalid student ID. Please try again.")
            return redirect('personel')
        
        try:
            ticket_id = int(ticket_id)
            student = get_object_or_404(Appointments, id=ticket_id)

            if action == "standby":
                # Check if student is already standby
                if student.status == "standby":
                    messages.info(request, f"Student {student.ticket_number} is already on standby.")
                else:
                    student.status = "standby"
                    student.save()
                    broadcast_update()
                    broadcast_queue_update()
                    messages.success(request, f"Priority student {student.ticket_number} moved to standby.")
                    
                    # If queue is running and no current student, auto-start serving
                    if is_queue_running():
                        today = timezone.now().date()
                        current_student = Appointments.objects.filter(
                            status="current",
                            datetime__date=today
                        ).first()
                        
                        if not current_student:
                            # Calculate served count
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
                                messages.info(request, f"Auto-started serving next student: {next_student.ticket_number}")

        except (ValueError, TypeError):
            messages.error(request, "Invalid student ID format.")
        except Appointments.DoesNotExist:
            messages.error(request, "Student not found.")

    return redirect("personel")




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
    if request.user.is_authenticated:
        return redirect('personel')
    
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
    if request.user.is_authenticated:
        return redirect('personel')
    
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


