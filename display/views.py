from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import loader
from personel.models import Appointments, RequestType, Courses
from django.utils import timezone
from datetime import timedelta
from django.utils.timezone import localtime
from django.http import JsonResponse

# Create your views here.
def home(request):
    template = loader.get_template('display/home.html')
    context = {
        
    }
    return HttpResponse(template.render(context, request))


def current_serving(request):
    template = loader.get_template('display/current_serving.html')
    context = {
        
    }
    return HttpResponse(template.render(context, request))