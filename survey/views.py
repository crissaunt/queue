from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse
from django.template import loader
from personel.models import Code
from .models import (
    ClientType, CCchoices, CCquestion,
    ServiceQualityDimension, SQDResponse,
    SatisfactionSurvey, CCResponse, SurveyYear,
    QuestionYear, SQDYear
)
from django.db.models import Q
from django.db import transaction

def mark_survey_used(code_id):
    """
    Marks a survey code as used (without WebSocket updates).
    WebSocket updates should be handled by the personnel app.
    """
    try:
        survey = Code.objects.get(id=code_id)
        survey.status = "used"
        survey.save()
        print(f"✅ Survey code {survey.code} marked as used")
        return True
    except Code.DoesNotExist:
        print(f"❌ Code with id {code_id} does not exist")
        return False

# ---------------- HOME ----------------
def home(request):
    return render(request, "survey/home.html")


# ---------------- CODE VALIDATION ----------------
def validate_code(request):
    if request.method == 'POST':
        get_code = request.POST.get("code")
        print("Submitted code:", get_code)

        code_obj = Code.objects.filter(code=get_code).first()
        if code_obj:
            if code_obj.status == "used":
                print("❌ Code has already been used.")
                messages.error(request, "This code has already been used!")
                return redirect('survey')
            else:
                print("Found code:", code_obj.code, "Status:", code_obj.status)
                request.session['code_obj'] = get_code
                print("✅ Code stored in session")
                print("SESSION STATE:", dict(request.session))
                return redirect('form')
        else:
            print("❌ Code not found.")
            messages.error(request, "Code not found!")

    return redirect('survey')



# ---------------- PAGE 1 ----------------
def form(request):
    if not request.session.get('code_obj'):
        return redirect('survey')

    client_types = ClientType.objects.all()
    return render(request, "survey/form.html", {"client_type": client_types})

def validate_form(request):
    if request.method == 'POST':
        code_value = request.session.get('code_obj')
        code_obj = Code.objects.filter(code=code_value).first()
        if not code_obj:
            return redirect('survey')

        # DEBUG: Print what we're receiving
        print("DEBUG - Form POST data:")
        for key, value in request.POST.items():
            print(f"  {key}: {value} (type: {type(value)})")
        
        # ✅ Store all form values in session
        request.session['form_data'] = {
            "client_type_id": request.POST.get('client_type'),
            "date": request.POST.get('date'),
            "sex": request.POST.get('sex'),
            "age": request.POST.get('age'),
            "government": request.POST.get('government'),
            "region": request.POST.get('region'),
            "person_visited": request.POST.get('person_visited'),
            "service_availed": request.POST.get('service_availed'),
        }

        print("✅ Form data stored in session:", request.session['form_data'])
        print("SESSION STATE:", dict(request.session))

        return redirect('question1')

    return redirect('survey')



# ---------------- PAGE 2 (CC Questions) ----------------
def question1(request):
    if not request.session.get('code_obj'):
        return redirect('survey')

    # Get the current year (latest SurveyYear)
    current_year = SurveyYear.objects.order_by('-year').first()

    # Get questions linked to this year
    questions = CCquestion.objects.filter(
        year_links__year=current_year
    ).prefetch_related("choices").distinct()

    return render(request, "survey/q1.html", {"questions": questions})


def validate_question1(request):
    if not request.session.get('code_obj'):
        return redirect('survey')

    if request.method == 'POST':
        cc_answers = {}

        # Get current year for filtering
        current_year = SurveyYear.objects.order_by('-year').first()
        
        # Only get questions for current year
        questions = CCquestion.objects.filter(
            year_links__year=current_year
        ).distinct()
        
        for question in questions:
            selected_choice = request.POST.get(f'choice_{question.id}')
            if selected_choice:
                cc_answers[str(question.id)] = int(selected_choice)

        # ✅ Save to session
        request.session['cc_answers'] = cc_answers  

        print("✅ CC Responses stored in session")
        print("SESSION STATE:", dict(request.session))

        return redirect('question2')

    return redirect('question1')



# ---------------- PAGE 3 (SQD Ratings) ----------------
def question2(request):
    if not request.session.get('code_obj'):
        return redirect('survey')

    # Get the current year (latest SurveyYear)
    current_year = SurveyYear.objects.order_by('-year').first()

    # Get SQDs linked to this year
    sqds = ServiceQualityDimension.objects.filter(
        year_links__year=current_year
    ).distinct()

    return render(request, "survey/q2.html", {"sqds": sqds})


def validate_question2(request):
    if not request.session.get('code_obj'):
        return redirect('survey')

    if request.method == "POST":
        code_obj = Code.objects.get(code=request.session.get('code_obj'))
        form_data = request.session.get('form_data', {})
        cc_answers = request.session.get('cc_answers', {})
        
        # DEBUG: Print form_data to see what's in it
        print("DEBUG - Form Data:", form_data)
        print("DEBUG - client_type_id value:", form_data.get("client_type_id"))
        print("DEBUG - Type of client_type_id:", type(form_data.get("client_type_id")))
        
        survey_year = SurveyYear.objects.order_by("-year").first()

        with transaction.atomic():
            # --- Create the survey ---
            try:
                # Safely convert client_type_id to int
                client_type_id = form_data.get("client_type_id")
                if client_type_id:
                    # Try to convert to int, if it fails, set to None
                    try:
                        client_type_id_int = int(client_type_id)
                    except (ValueError, TypeError):
                        client_type_id_int = None
                        print(f"WARNING: Could not convert client_type_id '{client_type_id}' to integer")
                else:
                    client_type_id_int = None
                
                # Safely convert age to int
                age_str = form_data.get("age")
                if age_str:
                    try:
                        age_int = int(age_str)
                    except (ValueError, TypeError):
                        age_int = None
                        print(f"WARNING: Could not convert age '{age_str}' to integer")
                else:
                    age_int = None
                
                survey = SatisfactionSurvey.objects.create(
                    code=code_obj,
                    survey_year=survey_year,  
                    client_type_id=client_type_id_int,  # Use the safely converted value
                    visit_date=form_data.get("date") or None,
                    sex=form_data.get("sex"),
                    age=age_int,  # Use the safely converted value
                    government=form_data.get("government"),
                    region=form_data.get("region"),
                    office_person=form_data.get("person_visited"),
                    service_availed=form_data.get("service_availed")
                )
                
            except Exception as e:
                print(f"ERROR creating survey: {e}")
                messages.error(request, "Error creating survey. Please try again.")
                return redirect('question2')

            # --- Save CC Responses ---
            for q_id, choice_id in cc_answers.items():
                try:
                    question = CCquestion.objects.get(id=int(q_id))
                    question_year = QuestionYear.objects.get(
                        year=survey.survey_year,
                        question=question
                    )
                    CCResponse.objects.create(
                        survey=survey,
                        question_year=question_year,
                        choice_id=choice_id
                    )
                except (QuestionYear.DoesNotExist, CCquestion.DoesNotExist) as e:
                    print(f"Warning: Could not save CC response for question {q_id}: {e}")
                    continue

            # --- Save SQD Responses ---
            # Get only SQDs for current year
            current_sqds = ServiceQualityDimension.objects.filter(
                year_links__year=survey.survey_year
            ).distinct()
            
            for sqd in current_sqds:
                rating_value = request.POST.get(f'rating_{sqd.id}')
                if rating_value:
                    try:
                        sqd_year = SQDYear.objects.get(
                            year=survey.survey_year,
                            sqd=sqd
                        )
                        SQDResponse.objects.create(
                            survey=survey,
                            sqd_year=sqd_year,
                            rating=int(rating_value)
                        )
                    except (SQDYear.DoesNotExist, ValueError) as e:
                        print(f"Warning: Could not save SQD response for {sqd.name}: {e}")
                        continue

            # --- Feedback + email ---
            feedback = request.POST.get("feedback")
            email = request.POST.get("email")
            if feedback or email:
                survey.feedback = feedback
                survey.email = email
                survey.save()

            # --- Mark code as used (without WebSocket updates) ---
            if code_obj.status == 'unused':
                # Use the simplified function without request parameter
                mark_survey_used(code_obj.id)

        # ✅ Selectively clear only survey-related session keys
        for key in ['code_obj', 'form_data', 'cc_answers']:
            request.session.pop(key, None)
        print("SESSION AFTER CLEAR:", dict(request.session))

        # ADD THIS: Redirect with success parameter
        messages.success(request, "Survey submitted successfully! Thank you for your feedback.")
        return redirect(f"{reverse('survey')}?submitted=true")

    return redirect('question2')