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

class RequestType(models.Model):
    request = models.CharField(max_length=100)

    def __str__(self):
        return self.request

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
        ('standby', 'Standby')
    ]
    USER_TYPE = [
        ('student', 'Student'),
        ('guest', 'Guest'),
    ]

    firstName = models.CharField(max_length=50)
    middleName = models.CharField(max_length=1, blank=True)
    lastName = models.CharField(max_length=50)
    datetime = models.DateTimeField(default=timezone.now)
    ticket_number = models.CharField(max_length=10, null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    user_type = models.CharField(max_length=50, choices=USER_TYPE, default='student')
    is_priority = models.CharField(max_length=50, choices=[('yes','Yes'),('no','No')], default='no')
    
    # relationships 
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
        Cancel all pending, current, skip, and standby appointments after midnight.
        This should be run daily via cron job.
        """
        # Statuses to cancel at end of day
        statuses_to_cancel = ['pending', 'current', 'skip', 'standby']
        
        # Get today's date
        today = timezone.localdate()
        
        # Cancel appointments that are from today or earlier with the specified statuses
        expired_appointments = cls.objects.filter(
            status__in=statuses_to_cancel,
            datetime__date__lte=today  # Includes today and past dates
        )
        
        count = expired_appointments.count()
        print(f"🎯 Cancelling {count} appointments with statuses: {statuses_to_cancel}")
        
        expired_appointments.update(status='cancel')
        
        return count

    @classmethod
    def cancel_outdated(cls):
        """
        Automatically cancel appointments from previous days that are still active.
        This can be called from anywhere to clean up outdated appointments.
        """
        today = timezone.localdate()
        statuses_to_cancel = ['pending', 'current', 'skip', 'standby']
        
        outdated_appointments = cls.objects.filter(
            datetime__date__lt=today,  # Only previous days
            status__in=statuses_to_cancel
        )
        
        count = outdated_appointments.count()
        if count > 0:
            print(f"🕒 Auto-cancelling {count} outdated appointments from previous days")
            outdated_appointments.update(status='cancel')
        
        return count

    @classmethod
    def get_today_appointments(cls):
        """
        Helper method to get only today's appointments with active statuses.
        """
        today = timezone.localdate()
        return cls.objects.filter(datetime__date=today)

    @classmethod
    def get_current_student(cls):
        """
        Get current student from today only.
        """
        today = timezone.localdate()
        return cls.objects.filter(
            status="current",
            datetime__date=today
        ).first()

    def __str__(self):
        return f'{self.firstName} {self.lastName}'
    # Add this to your Appointments model in models.py
    @classmethod
    def cancel_expired_skips(cls):
        """
        Cancel skip appointments where skip_until time has passed.
        """
        from django.utils import timezone
        now = timezone.now()
        
        expired_skips = cls.objects.filter(
            status="skip",
            skip_until__lt=now,
            skip_until__isnull=False  # Only where skip_until is set
        )
        
        count = expired_skips.count()
        if count > 0:
            print(f"⏰ Auto-cancelling {count} expired skip appointments")
            expired_skips.update(status='cancel')
        
        return count

class Code(models.Model):
    STATUS_CHOICES = [
        ('unused', 'Unused'),
        ('used', 'Used'),
    ]
    appointments = models.ForeignKey(Appointments, on_delete=models.PROTECT,  null=True)
    code = models.CharField(max_length=10, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unused' , null=True)

    def __str__(self):
        return self.code
    
# models.py
class QueueControl(models.Model):
    is_running = models.BooleanField(default=True)

    def __str__(self):
        return "Queue Running" if self.is_running else "Queue Stopped"
    
    @classmethod
    def get_queue_control(cls):
        """Get or create the queue control object"""
        obj, created = cls.objects.get_or_create(id=1)
        return obj

    


