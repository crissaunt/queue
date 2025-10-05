from django.db import models
from personel.models import Code


class ClientType(models.Model):
    name = models.CharField(max_length=100, unique=True, null=True)

    def __str__(self):
        return self.name


# 🔗 Survey Year (organizer for questions + SQDs)
class SurveyYear(models.Model):
    year = models.PositiveIntegerField(unique=True, null=True)

    def __str__(self):
        return str(self.year)


# =========================
# CUSTOMER CARE QUESTIONS
# =========================
class CCquestion(models.Model):
    name = models.CharField(max_length=255,null=True)
    created_at = models.DateTimeField(auto_now_add=True,null=True)
    updated_at = models.DateTimeField(auto_now=True,null=True)

    def __str__(self):
        return self.name

    @property
    def choices_list(self):
        """Return choices as a list of strings for JavaScript"""
        return list(self.choices.values_list('name', flat=True))


class CCchoices(models.Model):
    name = models.CharField(max_length=100, null=True)
    question = models.ForeignKey(CCquestion, on_delete=models.CASCADE, related_name="choices", null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.question.name} → {self.name}"


# 🔗 Mapping Question ↔ Year
class QuestionYear(models.Model):
    year = models.ForeignKey(SurveyYear, on_delete=models.CASCADE, related_name="question_links", null=True)
    question = models.ForeignKey(CCquestion, on_delete=models.CASCADE, related_name="year_links", null=True)

    class Meta:
        unique_together = ("year", "question")

    def __str__(self):
        return f"{self.question.name} ({self.year})"


# =========================
# SERVICE QUALITY DIMENSIONS
# =========================
class ServiceQualityDimension(models.Model):
    name = models.CharField(max_length=100, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.name


# 🔗 Mapping SQD ↔ Year
class SQDYear(models.Model):
    year = models.ForeignKey(SurveyYear, on_delete=models.CASCADE, related_name="sqd_links", null=True)
    sqd = models.ForeignKey(ServiceQualityDimension, on_delete=models.CASCADE, related_name="year_links", null=True)

    class Meta:
        unique_together = ("year", "sqd")

    def __str__(self):
        return f"{self.sqd.name} ({self.year})"


# =========================
# SATISFACTION SURVEY (PAGE 1)
# =========================
class SatisfactionSurvey(models.Model):
    code = models.OneToOneField(Code, on_delete=models.PROTECT, null=True)

    # Which year’s survey this belongs to
    survey_year = models.ForeignKey(SurveyYear, on_delete=models.CASCADE, related_name="surveys", null=True)

    # Page 1 fields
    client_type = models.ForeignKey(ClientType, on_delete=models.SET_NULL, null=True)
    government = models.CharField(max_length=50, null=True, default="government")

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
        return f"Survey {self.id} ({self.survey_year}) - {self.client_type}"


# =========================
# PAGE 2 RESPONSES (Questions)
# =========================
class CCResponse(models.Model):
    survey = models.ForeignKey(SatisfactionSurvey, on_delete=models.CASCADE, related_name="cc_responses" ,null=True)
    question_year = models.ForeignKey("QuestionYear", on_delete=models.CASCADE, related_name="responses" ,null=True)
    choice = models.ForeignKey(CCchoices, on_delete=models.CASCADE, null=True)  # only 1 answer per question
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.survey} - {self.question_year.question.name}: {self.choice.name}"



# =========================
# PAGE 3 RESPONSES (SQDs)
# =========================
class SQDResponse(models.Model):
    survey = models.ForeignKey(SatisfactionSurvey, on_delete=models.CASCADE, related_name="sqd_responses", null=True)
    sqd_year = models.ForeignKey(SQDYear, on_delete=models.CASCADE, related_name="responses", null=True)
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)], null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.survey} - {self.sqd_year.sqd.name}: {self.rating} star(s)"
