from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import loader
from personel.models import StudentAppointments
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import localtime

today = timezone.now().date()
def home(request):
    today = timezone.now().date()

    get_current_number = StudentAppointments.objects.filter(
        status="current",
        datetime__date=today
    ).order_by("datetime").first()

    # Collect possible "next in line"
    candidates = []

    # 1. Priority Standby
    priority_standby = StudentAppointments.objects.filter(
        status="standby",
        is_priority="yes",
        datetime__date=today
    ).order_by("datetime")

    # 2. Regular Standby
    regular_standby = StudentAppointments.objects.filter(
        status="standby",
        is_priority="no",
        datetime__date=today
    ).order_by("datetime")

    # 3. Priority Pending (if you want to include it, uncomment)
    # priority_pending = StudentAppointments.objects.filter(
    #     status="pending",
    #     is_priority="yes",
    #     datetime__date=today
    # ).order_by("datetime")

    # 4. Regular Pending
    regular_pending = StudentAppointments.objects.filter(
        status="pending",
        is_priority="no",
        datetime__date=today
    ).order_by("datetime")

    # Merge all respecting order
    candidates = list(priority_standby) + list(regular_standby) + list(regular_pending)

    # Slice top 10
    next_in_line = candidates[:5]

    template = loader.get_template('students/home.html')
    context = {
        'get_current_number': get_current_number,
        'next_in_line': next_in_line
    }
    return HttpResponse(template.render(context, request))

