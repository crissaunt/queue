
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.template import loader
from django.contrib import messages
from django.db import transaction

from survey.models import SurveyYear, CCquestion, CCchoices, QuestionYear, ServiceQualityDimension, SQDYear,SatisfactionSurvey

# Create your views here.


def home(request):
    template = loader.get_template('dashboard/home.html')
    context = {

    }
    return HttpResponse(template.render(context, request))




# =========================
# SURVEY YEAR MANAGEMENT
# =========================
def survey_year_list(request):
    """List all survey years"""
    years = SurveyYear.objects.all().order_by('-year')
    template = loader.get_template('dashboard/manage/years.html')
    context = {
        'years': years,
    }
    return HttpResponse(template.render(context, request))

def create_survey_year(request):
    """Create a new survey year"""
    if request.method == 'POST':
        year = request.POST.get('year')
        if year:
            try:
                SurveyYear.objects.create(year=year)
                messages.success(request, f"Survey year {year} created successfully!")
            except:
                messages.error(request, "Survey year already exists!")
        else:
            messages.error(request, "Year is required!")
    
    return redirect('survey_year_list')

def delete_survey_year(request, year_id):
    """Delete a survey year"""
    year = get_object_or_404(SurveyYear, id=year_id)
    year.delete()
    messages.success(request, f"Survey year {year.year} deleted!")
    return redirect('survey_year_list')

# =========================
# QUESTION MANAGEMENT
# =========================
def question_list(request):
    """List all questions with their assigned years"""
    questions = CCquestion.objects.all().prefetch_related('year_links__year', 'choices')
    available_years = SurveyYear.objects.all()
    
    # Create a list of questions with their choices for the template
    questions_with_choices = []
    for question in questions:
        # Create a simple list of choice names for the template
        choices_list = [choice.name for choice in question.choices.all()]
        
        # Add the choices_list as a regular attribute (not using the property)
        question.choices_list_data = choices_list
        questions_with_choices.append(question)
    
    template = loader.get_template('dashboard/manage/questions.html')
    context = {
        'questions': questions_with_choices,
        'available_years': available_years,
    }
    return HttpResponse(template.render(context, request))

def create_question(request):
    """Create a new question with choices"""
    if request.method == 'POST':
        question_text = request.POST.get('question_text')
        choices_text = request.POST.get('choices_text', '')
        
        if question_text:
            try:
                with transaction.atomic():
                    # Create question
                    question = CCquestion.objects.create(name=question_text)
                    
                    # Create choices (split by newline)
                    if choices_text:
                        choice_list = [choice.strip() for choice in choices_text.split('\n') if choice.strip()]
                        for choice_text in choice_list:
                            CCchoices.objects.create(
                                name=choice_text,
                                question=question
                            )
                    
                    messages.success(request, "Question created successfully!")
            except Exception as e:
                messages.error(request, f"Error creating question: {str(e)}")
        else:
            messages.error(request, "Question text is required!")
    
    return redirect('question_list')

def edit_question(request, question_id):
    """Edit a question and its choices"""
    question = get_object_or_404(CCquestion, id=question_id)
    
    if request.method == 'POST':
        question_text = request.POST.get('question_text')
        choices_text = request.POST.get('choices_text', '')
        
        if question_text:
            try:
                with transaction.atomic():
                    # Update question
                    question.name = question_text
                    question.save()
                    
                    # Clear existing choices and create new ones
                    question.choices.all().delete()
                    
                    if choices_text:
                        choice_list = [choice.strip() for choice in choices_text.split('\n') if choice.strip()]
                        for choice_text in choice_list:
                            CCchoices.objects.create(
                                name=choice_text,
                                question=question
                            )
                    
                    messages.success(request, "Question updated successfully!")
                    return redirect('question_list')
            except Exception as e:
                messages.error(request, f"Error updating question: {str(e)}")
        else:
            messages.error(request, "Question text is required!")
    
    # If GET request or error, return to question list
    return redirect('question_list')

def delete_question(request, question_id):
    """Delete a question"""
    question = get_object_or_404(CCquestion, id=question_id)
    question.delete()
    messages.success(request, "Question deleted successfully!")
    return redirect('question_list')

# =========================
# QUESTION-YEAR ASSIGNMENT
# =========================
def assign_question_to_year(request):
    """Assign a question to a survey year (reuse question)"""
    if request.method == 'POST':
        question_id = request.POST.get('question_id')
        year_id = request.POST.get('year_id')
        
        if question_id and year_id:
            try:
                question = CCquestion.objects.get(id=question_id)
                year = SurveyYear.objects.get(id=year_id)
                
                # Check if already assigned
                if not QuestionYear.objects.filter(question=question, year=year).exists():
                    QuestionYear.objects.create(question=question, year=year)
                    messages.success(request, f"Question assigned to {year.year} successfully!")
                else:
                    messages.warning(request, "Question is already assigned to this year!")
                    
            except (CCquestion.DoesNotExist, SurveyYear.DoesNotExist):
                messages.error(request, "Invalid question or year!")
        else:
            messages.error(request, "Both question and year are required!")
    
    return redirect('question_list')

def remove_question_from_year(request, assignment_id):
    """Remove a question from a survey year"""
    assignment = get_object_or_404(QuestionYear, id=assignment_id)
    year = assignment.year.year
    assignment.delete()
    messages.success(request, f"Question removed from {year}!")
    return redirect('question_list')

# =========================
# SURVEY CONFIGURATION BY YEAR
# =========================
from django.utils import timezone
from datetime import datetime


def configure_survey_year(request, year_id):
    """Configure which questions and SQDs are used for a specific year"""
    year = get_object_or_404(SurveyYear, id=year_id)
    
    # Check if this is a past year (current year or future years are editable)
    current_year = datetime.now().year
    is_past_year = year.year < current_year
    is_readonly = is_past_year
    
    # Get assigned question IDs for this year
    assigned_question_ids = QuestionYear.objects.filter(year=year).values_list('question_id', flat=True)
    
    # Get assigned SQD IDs for this year
    assigned_sqd_ids = SQDYear.objects.filter(year=year).values_list('sqd_id', flat=True)
    
    if is_past_year:
        # For past years: Show ONLY assigned questions and SQDs
        assigned_questions = CCquestion.objects.filter(id__in=assigned_question_ids).prefetch_related('choices')
        assigned_sqds = ServiceQualityDimension.objects.filter(id__in=assigned_sqd_ids)
        available_questions = CCquestion.objects.none()  # Empty queryset
        available_sqds = ServiceQualityDimension.objects.none()  # Empty queryset
    else:
        # For current/future years: Show ALL questions and SQDs
        assigned_questions = CCquestion.objects.filter(id__in=assigned_question_ids).prefetch_related('choices')
        available_questions = CCquestion.objects.exclude(id__in=assigned_question_ids).prefetch_related('choices')
        assigned_sqds = ServiceQualityDimension.objects.filter(id__in=assigned_sqd_ids)
        available_sqds = ServiceQualityDimension.objects.exclude(id__in=assigned_sqd_ids)
    
    if request.method == 'POST':
        # Prevent editing past years
        if is_past_year:
            messages.error(request, f"Cannot modify survey configuration for past year {year.year}. Data integrity must be maintained.")
            return redirect('configure_survey_year', year_id=year_id)
        
        # Handle question assignments
        question_ids = request.POST.getlist('questions')
        QuestionYear.objects.filter(year=year).delete()  # Clear existing
        
        for question_id in question_ids:
            question = CCquestion.objects.get(id=question_id)
            QuestionYear.objects.create(question=question, year=year)
        
        # Handle SQD assignments
        sqd_ids = request.POST.getlist('sqds')
        SQDYear.objects.filter(year=year).delete()  # Clear existing
        
        for sqd_id in sqd_ids:
            sqd = ServiceQualityDimension.objects.get(id=sqd_id)
            SQDYear.objects.create(sqd=sqd, year=year)
        
        messages.success(request, f"Survey configuration for {year.year} updated successfully!")
        return redirect('configure_survey_year', year_id=year_id)
    
    template = loader.get_template('dashboard/manage/configure_year.html')
    context = {
        'year': year,
        'assigned_questions': assigned_questions,
        'available_questions': available_questions,
        'assigned_sqds': assigned_sqds,
        'available_sqds': available_sqds,
        'assigned_question_ids': list(assigned_question_ids),
        'assigned_sqd_ids': list(assigned_sqd_ids),
        'is_readonly': is_readonly,
        'is_past_year': is_past_year,
        'current_year': current_year,
    }
    return HttpResponse(template.render(context, request))
# =========================
# SQD MANAGEMENT
# =========================
def sqd_list(request):
    """List all Service Quality Dimensions"""
    sqds = ServiceQualityDimension.objects.all().prefetch_related('year_links__year')
    available_years = SurveyYear.objects.all()
    
    template = loader.get_template('dashboard/manage/sqd.html')
    context = {
        'sqds': sqds,
        'available_years': available_years,
    }
    return HttpResponse(template.render(context, request))

def create_sqd(request):
    """Create a new Service Quality Dimension"""
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            ServiceQualityDimension.objects.create(name=name)
            messages.success(request, "SQD created successfully!")
        else:
            messages.error(request, "SQD name is required!")
    
    return redirect('sqd_list')

def assign_sqd_to_year(request):
    """Assign a SQD to a survey year"""
    if request.method == 'POST':
        sqd_id = request.POST.get('sqd_id')
        year_id = request.POST.get('year_id')
        
        if sqd_id and year_id:
            try:
                sqd = ServiceQualityDimension.objects.get(id=sqd_id)
                year = SurveyYear.objects.get(id=year_id)
                
                if not SQDYear.objects.filter(sqd=sqd, year=year).exists():
                    SQDYear.objects.create(sqd=sqd, year=year)
                    messages.success(request, f"SQD assigned to {year.year} successfully!")
                else:
                    messages.warning(request, "SQD is already assigned to this year!")
                    
            except (ServiceQualityDimension.DoesNotExist, SurveyYear.DoesNotExist):
                messages.error(request, "Invalid SQD or year!")
        else:
            messages.error(request, "Both SQD and year are required!")
    
    return redirect('sqd_list')

# =========================
# API ENDPOINTS
# =========================
def get_questions_for_year(request, year_id):
    """API endpoint to get questions for a specific year"""
    year = get_object_or_404(SurveyYear, id=year_id)
    question_years = QuestionYear.objects.filter(year=year).select_related('question')
    
    questions_data = []
    for qy in question_years:
        questions_data.append({
            'id': qy.question.id,
            'text': qy.question.name,
            'choices': [
                {'id': choice.id, 'text': choice.name} 
                for choice in qy.question.choices.all()
            ]
        })
    
    return JsonResponse({'questions': questions_data})

def get_sqds_for_year(request, year_id):
    """API endpoint to get SQDs for a specific year"""
    year = get_object_or_404(SurveyYear, id=year_id)
    sqd_years = SQDYear.objects.filter(year=year).select_related('sqd')
    
    sqds_data = [{
        'id': sy.sqd.id,
        'name': sy.sqd.name
    } for sy in sqd_years]
    
    return JsonResponse({'sqds': sqds_data})


# Satisfaction Surveys
def satisfaction_survey_list(request):
    """List all satisfaction surveys"""
    surveys = SatisfactionSurvey.objects.all().select_related(
        'survey_year', 
        'client_type', 
        'code'
    ).prefetch_related(
        'cc_responses',
        'sqd_responses'
    ).order_by('-submitted_at')  # Changed from 'created_at' to 'submitted_at'
    
    template = loader.get_template('dashboard/manage/satisfaction_surveys.html')
    context = {
        'surveys': surveys,
    }
    return HttpResponse(template.render(context, request))

def delete_satisfaction_survey(request, survey_id):
    """Delete a satisfaction survey and all related responses"""
    survey = get_object_or_404(SatisfactionSurvey, id=survey_id)
    
    if request.method == 'POST':
        survey.delete()
        messages.success(request, "Survey deleted successfully!")
    
    return redirect('satisfaction_survey_list')


def view_satisfaction_survey(request, survey_id):
    """View detailed information about a specific satisfaction survey"""
    survey = get_object_or_404(SatisfactionSurvey.objects.select_related(
        'survey_year', 
        'client_type', 
        'code'
    ).prefetch_related(
        'cc_responses__question_year__question',
        'cc_responses__choice',
        'sqd_responses__sqd_year__sqd'
    ), id=survey_id)
    
    template = loader.get_template('dashboard/manage/view_satisfaction_survey.html')
    context = {
        'survey': survey,
    }
    return HttpResponse(template.render(context, request))