from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from django.contrib.auth.models import User




class Personel(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.user.username
    


# request ug id, pahimog id 
class RequestType(models.Model):
    request = models.CharField(max_length=100)

    def __str__(self):
        return self.request
    

# ex . ceit, cba 
class Courses(models.Model):
    courses = models.CharField(max_length=50, null=True)
    name = models.CharField(max_length=100, null=True)
    
    def __str__(self):
        return self.courses






class Appointments(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('current', 'Current'),
        ('done', 'Done'),
        ('skip', 'Skip'),
        ('cancel', 'Cancel'),
        ('standby', 'Standby' )
    ]
    USER_TYPE = [
        ('student', 'Student'),
        ('guest', 'Guest'),
    ]


    firstName = models.CharField(max_length=50)
    middleName = models.CharField(max_length=1, blank=True)
    lastName = models.CharField(max_length=50)
    # email = models.CharField(max_length=50)
    datetime = models.DateTimeField(default=timezone.now)
    ticket_number = models.CharField(max_length=10, null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')

    user_type = models.CharField(max_length=50, choices=USER_TYPE, default='student')

    is_priority = models.CharField(max_length=50, choices=[('yes','Yes'),('no','No')], default='no')
    # relationship 
    requestType = models.ForeignKey(RequestType, on_delete=models.CASCADE, null=True, blank=True)
    custom_request = models.CharField(max_length=200, null=True, blank=True) 
    courses = models.ForeignKey(Courses, on_delete=models.CASCADE, null=True, blank=True)


    served_by = models.ForeignKey(
        'Personel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments_served"
    )

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
            
    @classmethod
    def cancel_expired(cls):
        """
        Cancel only appointments whose datetime is in the past
        and whose status is pending or skip.
        """
        now = timezone.localdate()
        expired_appointments = cls.objects.filter(
            Q(status='pending') | Q(status='skip'),
            datetime__date__lt=now 
        )
        print(expired_appointments)
        expired_appointments.update(status='cancel')   

    def __str__(self):
        return f'{self.firstName} {self.lastName}'






    

