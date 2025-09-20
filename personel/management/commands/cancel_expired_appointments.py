from django.core.management.base import BaseCommand
from personel.models import Appointments

class Command(BaseCommand):
    help = "Cancel expired appointments"

    def handle(self, *args, **kwargs):
        Appointments.cancel_expired()
        self.stdout.write("Expired appointments canceled successfully.")
