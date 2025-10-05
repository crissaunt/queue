from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home ,name='dashboard'),
    # Survey Year Management
    path('years/', views.survey_year_list, name='survey_year_list'),
    path('years/create/', views.create_survey_year, name='create_survey_year'),
    path('years/<int:year_id>/delete/', views.delete_survey_year, name='delete_survey_year'),
    path('years/<int:year_id>/configure/', views.configure_survey_year, name='configure_survey_year'),
    
    # Question Management
    path('questions/', views.question_list, name='question_list'),
    path('questions/create/', views.create_question, name='create_question'),
    path('questions/<int:question_id>/edit/', views.edit_question, name='edit_question'),
    path('questions/<int:question_id>/delete/', views.delete_question, name='delete_question'),
    path('questions/assign/', views.assign_question_to_year, name='assign_question_to_year'),
    path('assignments/<int:assignment_id>/remove/', views.remove_question_from_year, name='remove_question_from_year'),
    
    # SQD Management
    path('sqds/', views.sqd_list, name='sqd_list'),
    path('sqds/create/', views.create_sqd, name='create_sqd'),
    path('sqds/assign/', views.assign_sqd_to_year, name='assign_sqd_to_year'),
    
    # API Endpoints
    path('api/years/<int:year_id>/questions/', views.get_questions_for_year, name='get_questions_for_year'),
    path('api/years/<int:year_id>/sqds/', views.get_sqds_for_year, name='get_sqds_for_year'),


    # Satisfaction Surveys
    path('surveys/satisfaction/', views.satisfaction_survey_list, name='satisfaction_survey_list'),
    path('surveys/satisfaction/<int:survey_id>/', views.view_satisfaction_survey, name='view_satisfaction_survey'),
    path('surveys/satisfaction/<int:survey_id>/delete/', views.delete_satisfaction_survey, name='delete_satisfaction_survey'),
  
]