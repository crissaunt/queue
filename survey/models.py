from django.db import models
from personel.models import Code


class ClientType(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class CCquestion(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class CCchoices(models.Model):
    name = models.CharField(max_length=100)
    question = models.ForeignKey(CCquestion, on_delete=models.CASCADE, related_name="choices")

    def __str__(self):
        return f"{self.question.name} → {self.name}"


class ServiceQualityDimension(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class SatisfactionSurvey(models.Model):
    code = models.OneToOneField(Code, on_delete=models.PROTECT, null=True)

    # Page 1
    client_type = models.ForeignKey(ClientType, on_delete=models.SET_NULL, null=True)
    government = models.CharField(max_length=50, null=True, default='government')

    visit_date = models.DateField(null=True)
    sex = models.CharField(max_length=20, null=True)
    age = models.IntegerField(null=True)
    region = models.CharField(max_length=100, null=True)
    office_person = models.CharField(max_length=100, null=True)
    service_availed = models.TextField(null=True)

    # Feedback + email
    feedback = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Survey {self.id} - {self.client_type}"


# ✅ Page 2 responses: each survey can answer many questions, 
# and each question can have multiple choices selected
class CCResponse(models.Model):
    survey = models.ForeignKey(SatisfactionSurvey, on_delete=models.CASCADE, related_name="cc_responses")
    question = models.ForeignKey(CCquestion, on_delete=models.CASCADE)
    choices = models.ManyToManyField(CCchoices)  # multiple selected choices

    def __str__(self):
        return f"{self.survey} - {self.question.name}"


# ✅ Page 3 responses: each survey can rate multiple SQDs
class SQDResponse(models.Model):
    survey = models.ForeignKey(SatisfactionSurvey, on_delete=models.CASCADE, related_name="sqd_responses")
    sqd = models.ForeignKey(ServiceQualityDimension, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])

    def __str__(self):
        return f"{self.survey} - {self.sqd.name}: {self.rating} star(s)"
