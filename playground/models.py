from django.db import models
from personel.models import Appointments

class Pin(models.Model):
    STATUS_CHOICES = [
        ('unused', 'Unused'),
        ('used', 'Used'),
    ]
    appointments = models.ForeignKey(Appointments, on_delete=models.PROTECT,  null=True)
    code = models.CharField(max_length=10, null=True)  # unique so duplicates are prevented
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unused' , null=True)

    def __str__(self):
        return self.code


class SatisfactionSurvey(models.Model):
    pin = models.OneToOneField(Pin, on_delete=models.PROTECT, null=True)


    # Page1 fields
    clientType = models.CharField(max_length=50)
    government = models.CharField(max_length=50)
    visitDate = models.DateField()
    sex = models.CharField(max_length=20)
    age = models.IntegerField()
    region = models.CharField(max_length=100)
    officePerson = models.CharField(max_length=100)
    serviceAvailed = models.TextField()

    # Page2 fields
    cc1 = models.CharField(max_length=200)   # stored as comma-separated (max 3)
    cc2 = models.CharField(max_length=5)
    cc3 = models.CharField(max_length=5)

    # Page3 ratings
    sod0 = models.IntegerField()
    sod1 = models.IntegerField()
    sod2 = models.IntegerField()
    sod3 = models.IntegerField()
    sod4 = models.IntegerField()
    sod5 = models.IntegerField()
    sod6 = models.IntegerField()
    sod7 = models.IntegerField()
    sod8 = models.IntegerField()

    # Feedback + email
    feedback = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True, null=True)

    submitted_at = models.DateTimeField(auto_now_add=True)

    
    def __str__(self):
        return f"Survey {self.id} - {self.clientType}"
    



