from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import loader
from personel.models import StudentAppointments
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import localtime

def home(request):
    template = loader.get_template('students/home.html')
    context = {

    }
    return HttpResponse(template.render(context, request))


def live_updates(request):
    template = loader.get_template('students/live_updates.html')
    context = {

    }
    return HttpResponse(template.render(context, request))

