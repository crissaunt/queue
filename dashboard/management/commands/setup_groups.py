# management/commands/setup_groups.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from personel.models import Appointments, RequestType, Courses
from survey.models import SatisfactionSurvey

class Command(BaseCommand):
    help = 'Create default user groups and permissions'

    def handle(self, *args, **options):
        # Admin group
        admin_group, created = Group.objects.get_or_create(name='Admin')
        
        # Staff group
        staff_group, created = Group.objects.get_or_create(name='Staff')
        
        # Viewer group
        viewer_group, created = Group.objects.get_or_create(name='Viewer')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully created user groups')
        )