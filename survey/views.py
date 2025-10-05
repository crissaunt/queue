from django.shortcuts import render, redirect
from django.contrib import messages

from django.http import HttpResponse
from django.template import loader
from personel.models import Code
from .models import (
    ClientType, CCchoices, CCquestion,
    ServiceQualityDimension, SQDResponse,
    SatisfactionSurvey, CCResponse
)
from .models import SatisfactionSurvey, CCquestion, CCchoices, CCResponse, QuestionYear, SQDYear


from django.db.models import Q


from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def mark_survey_used(request, code_id):
    survey = Code.objects.get(id=code_id)
    survey.status = "used"
    survey.save()

    # ✅ Send websocket update to refresh frontend
    channel_layer = get_channel_layer()
    surveys = Code.objects.filter(status="used").order_by("-created_at")[:20]
    survey_list = [
        {"code": s.code, "appointment": str(s.appointments), "status": s.status}
        for s in surveys
    ]

    async_to_sync(channel_layer.group_send)(
        "queue",  # same group
        {
            "type": "send_update",
            "data": {"surveys": survey_list}
        }
    )

    return redirect("personel")

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
                # You can add a message to the user instead of redirecting silently
                return redirect('survey')  # or render a template with an error
            else:
                print("Found code:", code_obj.code, "Status:", code_obj.status)
                request.session['code_obj'] = get_code
                print("✅ Code stored in session")
                print("SESSION STATE:", dict(request.session))
                return redirect('form')
        else:
            print("❌ Code not found.")
            messages.error(request, " Code not found!")

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

        print("✅ Form data stored in session")
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

        for question in CCquestion.objects.all():
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




from django.db import transaction
from .models import SurveyYear

def validate_question2(request):
    if not request.session.get('code_obj'):
        return redirect('survey')

    if request.method == "POST":
        code_obj = Code.objects.get(code=request.session.get('code_obj'))
        form_data = request.session.get('form_data', {})
        cc_answers = request.session.get('cc_answers', {})

        survey_year = SurveyYear.objects.order_by("-year").first()

        with transaction.atomic():
            # --- Create the survey ---
            survey = SatisfactionSurvey.objects.create(
                code=code_obj,
                survey_year=survey_year,  
                client_type_id=int(form_data.get("client_type_id")) if form_data.get("client_type_id") else None,
                visit_date=form_data.get("date") or None,
                sex=form_data.get("sex"),
                age=int(form_data.get("age")) if form_data.get("age") else None,
                government=form_data.get("government"),
                region=form_data.get("region"),
                office_person=form_data.get("person_visited"),
                service_availed=form_data.get("service_availed")
            )

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
                except QuestionYear.DoesNotExist:
                    continue

            # --- Save SQD Responses ---
            for sqd in ServiceQualityDimension.objects.all():
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
                    except SQDYear.DoesNotExist:
                        continue

            # --- Feedback + email ---
            feedback = request.POST.get("feedback")
            email = request.POST.get("email")
            if feedback or email:
                survey.feedback = feedback
                survey.email = email
                survey.save()

            # --- Mark code as used ---
            if code_obj.status == 'unused':
                code_obj.status = 'used'
                mark_survey_used(request, code_obj.id)
                code_obj.save()

        # ✅ Selectively clear only survey-related session keys
        for key in ['code_obj', 'form_data', 'cc_answers']:
            request.session.pop(key, None)
        print("SESSION AFTER CLEAR:", dict(request.session))

        return redirect('survey')

    return redirect('question2')


