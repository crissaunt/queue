from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import loader
from personel.models import Code
from .models import (
    ClientType, CCchoices, CCquestion,
    ServiceQualityDimension, SQDResponse,
    SatisfactionSurvey, CCResponse
)


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
            print("Found code:", code_obj.code, "Status:", code_obj.status)
            if code_obj.status == 'unused':
                code_obj.status = 'used'
                code_obj.save()
                request.session['code_obj'] = get_code
                print("✅ Code stored in session")
                print("SESSION STATE:", dict(request.session))
                return redirect('form')
            else:
                print("⚠️ Code already used.")
        else:
            print("❌ Code not found.")

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

        client_type_id = request.POST.get('client_type')
        date = request.POST.get('date')
        sex = request.POST.get('sex')
        age = request.POST.get('age')
        government = request.POST.get('government')
        region = request.POST.get('region')
        person_visited = request.POST.get('person_visited')
        service_availed = request.POST.get('service_availed')

        survey = SatisfactionSurvey.objects.create(
            code=code_obj,
            client_type_id=int(client_type_id) if client_type_id else None,
            visit_date=date if date else None,
            sex=sex,
            age=int(age) if age else None,
            government=government,
            region=region,
            office_person=person_visited,
            service_availed=service_availed
        )

        request.session['survey_id'] = survey.id
        print("✅ Survey created and stored in session")
        print("SESSION STATE:", dict(request.session))
        return redirect('question1')

    return redirect('survey')


# ---------------- PAGE 2 (CC Questions) ----------------
def question1(request):
    if not request.session.get('survey_id'):
        return redirect('survey')

    questions = CCquestion.objects.prefetch_related("choices").all()
    return render(request, "survey/q1.html", {"questions": questions})


def validate_question1(request):
    survey_id = request.session.get('survey_id')
    if not survey_id:
        return redirect('survey')

    if request.method == 'POST':
        survey = SatisfactionSurvey.objects.get(id=survey_id)

        for question in CCquestion.objects.all():
            selected_choices = request.POST.getlist(f'choice_{question.id}')
            if selected_choices:
                response = CCResponse.objects.create(
                    survey=survey,
                    question=question
                )
                response.choices.set([int(c) for c in selected_choices])

        print("✅ CC Responses saved")
        print("SESSION STATE:", dict(request.session))
        return redirect('question2')

    return redirect('question1')


# ---------------- PAGE 3 (SQD Ratings) ----------------
def question2(request):
    if not request.session.get('survey_id'):
        return redirect('survey')

    sqds = ServiceQualityDimension.objects.all()
    return render(request, "survey/q2.html", {"sqds": sqds})



def validate_question2(request):
    survey_id = request.session.get('survey_id')
    if not survey_id:
        return redirect('survey')

    if request.method == "POST":
        survey = SatisfactionSurvey.objects.get(id=survey_id)

        # Save ratings
        for sqd in ServiceQualityDimension.objects.all():
            rating_value = request.POST.get(f'rating_{sqd.id}')
            if rating_value:
                SQDResponse.objects.create(
                    survey=survey,
                    sqd=sqd,
                    rating=int(rating_value)
                )

        # Save feedback and email
        feedback = request.POST.get("feedback")
        email = request.POST.get("email")

        if feedback or email:
            survey.feedback = feedback
            survey.email = email
            survey.save()

        print("✅ SQD Responses + Feedback/Email saved")
        print("SESSION STATE BEFORE CLEAR:", dict(request.session))

        # Clear session
        request.session.flush()

        print("SESSION STATE AFTER CLEAR:", dict(request.session))
        return redirect('survey')   # ⬅ back to home

    return redirect('question2')
