from django.db import models
from django.utils import timezone
from datetime import timedelta

# Create your models here.


# request ug id, pahimog id 
class RequestType(models.Model):
    request = models.CharField(max_length=100)

    def __str__(self):
        return self.request
    

# ex . ceit, cba 
class Courses(models.Model):
    courses = models.CharField(max_length=50, null=True)
    
    def __str__(self):
        return self.courses


# student, faculty, walk-in
class UserType(models.Model):
    name = models.CharField(max_length=50, unique=True, null=True)
    def __str__(self):
        return self.name



class StudentAppointments(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('current', 'Current'),
        ('done', 'Done'),
        ('skip', 'Skip'),
        ('cancel', 'Cancel'),
        ('standby', 'Standby' )
    ]
    idNumber= models.CharField(max_length=50, null=True)
    firstName = models.CharField(max_length=50)
    middleName = models.CharField(max_length=1)
    lastName = models.CharField(max_length=50)
    # email = models.CharField(max_length=50)
    datetime = models.DateTimeField(default=timezone.now)
    ticket_number = models.IntegerField(null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')

    is_priority = models.CharField(max_length=50, choices=[('yes','Yes'),('no','No')], default='no')
    # relationship 
    requestType = models.ForeignKey(RequestType, on_delete=models.CASCADE, null=True, blank=True)
    userType = models.ForeignKey(UserType, on_delete=models.CASCADE, null=True, blank=True)
    courses = models.ForeignKey(Courses, on_delete=models.CASCADE, null=True, blank=True)

    # NEW FIELDS
    skip_count = models.IntegerField(default=0)
    skip_until = models.DateTimeField(null=True, blank=True)

    def handle_skip(self):
        """
        Called whenever an appointment is skipped.
        """
        self.skip_count += 1
        self.status = 'skip'

        if self.skip_count >= 3:
            # Cancel immediately if skipped 3 times
            self.status = 'cancel'
            self.skip_until = None
        elif self.skip_count == 1:
            # Give 1 hour countdown
            self.skip_until = timezone.now() + timedelta(hours=1)
        self.save()
    def check_expiration(self):
        """
        Called by cron job / periodic task to check if skip timer expired.
        """
        if self.skip_until and timezone.now() > self.skip_until:
            self.status = 'cancel'
            self.save()    

    def __str__(self):
        return f'{self.firstName} {self.middleName} {self.lastName}'


# offices
class Offices(models.Model):
    name = models.CharField(max_length=100, null=True)
    def __str__(self):
        return f"{self.name}"