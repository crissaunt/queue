from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home ,name='survey'),
    path('validate/code', views.validate_code ,name='validate_code'),

    path('form/', views.form ,name='form'),
    path('validate/form/', views.validate_form ,name='validate_form'),

    path('question1/', views.question1 ,name='question1'),
    path('question1/validate/', views.validate_question1 ,name='validate_question1'),

    path('question2/', views.question2 ,name='question2'),
    path('question2/validate', views.validate_question2 ,name='validate_question2'),

  
]