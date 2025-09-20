# students/consumers.py
import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from personel.models import Appointments
from django.utils import timezone
from django.utils.timezone import localtime


class DisplayConsumer(WebsocketConsumer):
    def connect(self):
        self.group_name = "students_live_updates"
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()

        # Send initial data
        self.send_updates("Connected", initial=True)

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

    def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get("message", "update")
        self.send_updates(message)

    def chat_message(self, event):
        self.send_updates(event["message"])

    def send_updates(self, message, initial=False):
        now_ph = localtime(timezone.now())
        today = now_ph.date()

        # Auto-cancel expired skips
        expired = Appointments.objects.filter(
            status="skip", skip_until__lt=now_ph
        )
        for appt in expired:
            appt.status = "cancel"
            appt.save()

        # Current student
        if initial:
            get_current_number = Appointments.objects.filter(
                status="current",
            ).order_by("-datetime").first()
        else:
            get_current_number= Appointments.objects.filter(
                 status="current",
                datetime__date=today
            ).order_by("datetime").first()

        # Build payload (only current)
        payload = {
            "message": message,
            "current": {
                "id": get_current_number.id if get_current_number else None,
                "ticket_number": get_current_number.ticket_number if get_current_number else None,
                "firstName": get_current_number.firstName if get_current_number else None,
                "lastName": get_current_number.lastName if get_current_number else None,
                "status": get_current_number.status if get_current_number else None,
                "is_priority": get_current_number.is_priority if get_current_number else None,
                "user_type": get_current_number.user_type if get_current_number else None,
                "skip_count": get_current_number.skip_count or 0,
                "requestType": str(get_current_number.requestType) if get_current_number and get_current_number.requestType else None,
                "datetime": localtime(get_current_number.datetime).strftime("%H:%M")
                if get_current_number else None,
            } if get_current_number else None,
        }

        # Send to frontend
        self.send(text_data=json.dumps(payload))
