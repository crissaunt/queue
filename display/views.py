from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import loader
from personel.models import Appointments, RequestType, Courses
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import localtime
from django.http import JsonResponse


from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from personel.models import Appointments

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # Run daily at midnight to cancel expired appointments
    scheduler.add_job(
        Appointments.cancel_expired,
        trigger='cron',
        hour=0,
        minute=0,
        id='cancel_daily_appointments',
        replace_existing=True,
    )
    
    # Run every 5 minutes to clean up outdated appointments (from previous days)
    scheduler.add_job(
        Appointments.cancel_outdated,
        trigger='cron',
        minute='*/5',  # Every 5 minutes
        id='cancel_outdated_appointments',
        replace_existing=True,
    )
    
    # Run every 10 minutes to cancel expired skips
    scheduler.add_job(
        Appointments.cancel_expired_skips,
        trigger='cron',
        minute='*/10',  # Every 10 minutes
        id='cancel_expired_skips',
        replace_existing=True,
    )
    
    scheduler.start()

# Create your views here.
# def home(request):
#     template = loader.get_template('display/home.html')
#     context = {
        
#     }
#     return HttpResponse(template.render(context, request))


def current_serving(request):
    template = loader.get_template('display/current_serving.html')
    context = {
        
    }
    return HttpResponse(template.render(context, request))