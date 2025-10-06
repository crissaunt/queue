from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.template import loader
from django.contrib import messages
from django.db import transaction
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q
from survey.models import SurveyYear, CCquestion, CCchoices, QuestionYear, ServiceQualityDimension, SQDYear, SatisfactionSurvey
from personel.models import Appointments, Code, RequestType, Courses
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
# Create your views here.

from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q
from survey.models import SatisfactionSurvey, SurveyYear, CCquestion, ServiceQualityDimension,SQDResponse
from personel.models import Appointments, Code

@login_required
def home(request):
    """Dashboard focused on graphs and time-based analytics"""
    
    # Get time period from request or default to 7 days
    period = request.GET.get('period', '7days')
    
    # Calculate date ranges
    end_date = timezone.now().date()
    if period == '7days':
        start_date = end_date - timedelta(days=7)
        days_count = 7
    elif period == '30days':
        start_date = end_date - timedelta(days=30)
        days_count = 30
    else:  # month
        start_date = end_date - timedelta(days=90)
        days_count = 90
    
    # Generate date labels for charts
    date_labels = []
    current_date = start_date
    while current_date <= end_date:
        if period == '7days':
            date_labels.append(current_date.strftime('%a'))
        elif period == '30days':
            if current_date.day % 5 == 0 or current_date == start_date or current_date == end_date:
                date_labels.append(current_date.strftime('%m/%d'))
            else:
                date_labels.append('')
        else:  # monthly
            if current_date.day == 1 or current_date == start_date or current_date == end_date:
                date_labels.append(current_date.strftime('%b %Y'))
            else:
                date_labels.append('')
        current_date += timedelta(days=1)
    
    # Appointments data
    appointments_data = []
    surveys_data = []
    satisfaction_data = []
    
    current_date = start_date
    while current_date <= end_date:
        # Appointments count for this date
        appointments_count = Appointments.objects.filter(
            datetime__date=current_date
        ).count()
        appointments_data.append(appointments_count)
        
        # Surveys count for this date
        surveys_count = SatisfactionSurvey.objects.filter(
            submitted_at__date=current_date
        ).count()
        surveys_data.append(surveys_count)
        
        # Average satisfaction for this date
        daily_satisfaction = SQDResponse.objects.filter(
            survey__submitted_at__date=current_date
        ).aggregate(avg_rating=Avg('rating'))
        satisfaction_score = round(daily_satisfaction['avg_rating'] or 0, 1)
        satisfaction_data.append(satisfaction_score)
        
        current_date += timedelta(days=1)
    
    # Overall statistics for cards
    total_appointments = Appointments.objects.filter(
        datetime__date__range=[start_date, end_date]
    ).count()
    
    total_surveys = SatisfactionSurvey.objects.filter(
        submitted_at__date__range=[start_date, end_date]
    ).count()
    
    avg_satisfaction = SQDResponse.objects.filter(
        survey__submitted_at__date__range=[start_date, end_date]
    ).aggregate(avg_rating=Avg('rating'))
    avg_satisfaction_score = round(avg_satisfaction['avg_rating'] or 0, 1)
    
    response_rate = 0
    if total_appointments > 0:
        response_rate = round((total_surveys / total_appointments) * 100, 1)
    
    template = loader.get_template('dashboard/home.html')
    context = {
        'period': period,
        'date_labels': date_labels,
        'appointments_data': appointments_data,
        'surveys_data': surveys_data,
        'satisfaction_data': satisfaction_data,
        'total_appointments': total_appointments,
        'total_surveys': total_surveys,
        'avg_satisfaction_score': avg_satisfaction_score,
        'response_rate': response_rate,
        'start_date': start_date,
        'end_date': end_date,
    }
    return HttpResponse(template.render(context, request))

# =========================
# AUTHENTICATION VIEWS
# =========================
# In your views.py
def login_view(request):
    # If user is already authenticated, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    """User login view"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    
    # Use your template path
    return render(request, 'dashboard/auth/login.html', {'form': form})

def register_view(request):
    """User registration view"""
    # If user is already authenticated, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Auto-login after registration
            login(request, user)
            messages.success(request, "Registration successful! You are now logged in.")
            return redirect('dashboard')
        else:
            # Don't send individual error messages, let the form handle them
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserCreationForm()
    
    return render(request, 'dashboard/auth/register.html', {'form': form})

def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('dashboard')

# =========================
# PROTECTED VIEWS (Add login_required decorator to existing views)
# =========================

@login_required
def survey_year_list(request):
    """List all survey years"""
    years = SurveyYear.objects.all().order_by('-year')
    template = loader.get_template('dashboard/manage/years.html')
    context = {
        'years': years,
    }
    return HttpResponse(template.render(context, request))

@login_required
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

@login_required
def delete_survey_year(request, year_id):
    """Delete a survey year"""
    year = get_object_or_404(SurveyYear, id=year_id)
    year.delete()
    messages.success(request, f"Survey year {year.year} deleted!")
    return redirect('survey_year_list')

@login_required
def question_list(request):
    """List all questions with their assigned years"""
    questions = CCquestion.objects.all().prefetch_related('year_links__year', 'choices')
    available_years = SurveyYear.objects.all()
    
    questions_with_choices = []
    for question in questions:
        choices_list = [choice.name for choice in question.choices.all()]
        question.choices_list_data = choices_list
        questions_with_choices.append(question)
    
    template = loader.get_template('dashboard/manage/questions.html')
    context = {
        'questions': questions_with_choices,
        'available_years': available_years,
    }
    return HttpResponse(template.render(context, request))

@login_required
def create_question(request):
    """Create a new question with choices"""
    if request.method == 'POST':
        question_text = request.POST.get('question_text')
        choices_text = request.POST.get('choices_text', '')
        
        if question_text:
            try:
                with transaction.atomic():
                    question = CCquestion.objects.create(name=question_text)
                    
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

@login_required
def edit_question(request, question_id):
    """Edit a question and its choices"""
    question = get_object_or_404(CCquestion, id=question_id)
    
    if request.method == 'POST':
        question_text = request.POST.get('question_text')
        choices_text = request.POST.get('choices_text', '')
        
        if question_text:
            try:
                with transaction.atomic():
                    question.name = question_text
                    question.save()
                    
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
    
    return redirect('question_list')

@login_required
def delete_question(request, question_id):
    """Delete a question"""
    question = get_object_or_404(CCquestion, id=question_id)
    question.delete()
    messages.success(request, "Question deleted successfully!")
    return redirect('question_list')

@login_required
def assign_question_to_year(request):
    """Assign a question to a survey year (reuse question)"""
    if request.method == 'POST':
        question_id = request.POST.get('question_id')
        year_id = request.POST.get('year_id')
        
        if question_id and year_id:
            try:
                question = CCquestion.objects.get(id=question_id)
                year = SurveyYear.objects.get(id=year_id)
                
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

@login_required
def remove_question_from_year(request, assignment_id):
    """Remove a question from a survey year"""
    assignment = get_object_or_404(QuestionYear, id=assignment_id)
    year = assignment.year.year
    assignment.delete()
    messages.success(request, f"Question removed from {year}!")
    return redirect('question_list')

@login_required
def configure_survey_year(request, year_id):
    """Configure which questions and SQDs are used for a specific year"""
    year = get_object_or_404(SurveyYear, id=year_id)
    
    current_year = datetime.now().year
    is_past_year = year.year < current_year
    is_readonly = is_past_year
    
    assigned_question_ids = QuestionYear.objects.filter(year=year).values_list('question_id', flat=True)
    assigned_sqd_ids = SQDYear.objects.filter(year=year).values_list('sqd_id', flat=True)
    
    if is_past_year:
        assigned_questions = CCquestion.objects.filter(id__in=assigned_question_ids).prefetch_related('choices')
        assigned_sqds = ServiceQualityDimension.objects.filter(id__in=assigned_sqd_ids)
        available_questions = CCquestion.objects.none()
        available_sqds = ServiceQualityDimension.objects.none()
    else:
        assigned_questions = CCquestion.objects.filter(id__in=assigned_question_ids).prefetch_related('choices')
        available_questions = CCquestion.objects.exclude(id__in=assigned_question_ids).prefetch_related('choices')
        assigned_sqds = ServiceQualityDimension.objects.filter(id__in=assigned_sqd_ids)
        available_sqds = ServiceQualityDimension.objects.exclude(id__in=assigned_sqd_ids)
    
    if request.method == 'POST':
        if is_past_year:
            messages.error(request, f"Cannot modify survey configuration for past year {year.year}. Data integrity must be maintained.")
            return redirect('configure_survey_year', year_id=year_id)
        
        question_ids = request.POST.getlist('questions')
        QuestionYear.objects.filter(year=year).delete()
        
        for question_id in question_ids:
            question = CCquestion.objects.get(id=question_id)
            QuestionYear.objects.create(question=question, year=year)
        
        sqd_ids = request.POST.getlist('sqds')
        SQDYear.objects.filter(year=year).delete()
        
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

@login_required
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

@login_required
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

@login_required
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
@login_required
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

@login_required
def get_sqds_for_year(request, year_id):
    """API endpoint to get SQDs for a specific year"""
    year = get_object_or_404(SurveyYear, id=year_id)
    sqd_years = SQDYear.objects.filter(year=year).select_related('sqd')
    
    sqds_data = [{
        'id': sy.sqd.id,
        'name': sy.sqd.name
    } for sy in sqd_years]
    
    return JsonResponse({'sqds': sqds_data})

@login_required
def satisfaction_survey_list(request):
    """List all satisfaction surveys"""
    surveys = SatisfactionSurvey.objects.all().select_related(
        'survey_year', 
        'client_type', 
        'code'
    ).prefetch_related(
        'cc_responses',
        'sqd_responses'
    ).order_by('-submitted_at')
    
    template = loader.get_template('dashboard/manage/satisfaction_surveys.html')
    context = {
        'surveys': surveys,
    }
    return HttpResponse(template.render(context, request))

@login_required
def delete_satisfaction_survey(request, survey_id):
    """Delete a satisfaction survey and all related responses"""
    survey = get_object_or_404(SatisfactionSurvey, id=survey_id)
    
    if request.method == 'POST':
        survey.delete()
        messages.success(request, "Survey deleted successfully!")
    
    return redirect('satisfaction_survey_list')

@login_required
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