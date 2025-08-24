# chat/consumers.py
import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from personel.models import StudentAppointments
from django.utils import timezone
from django.utils.timezone import localtime


class StudentsConsumer(WebsocketConsumer):
    def connect(self):
        # We’ll just use a fixed group name (all live updates go here)
        self.group_name = "students_live_updates"

        # Join the group
        async_to_sync(self.channel_layer.group_add)(
            self.group_name,
            self.channel_name
        )

        self.accept()

        # Send initial data immediately when someone connects
        self.send_updates("Connected")

    def disconnect(self, close_code):
        # Leave group when disconnected
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )

    def receive(self, text_data):
        """
        When frontend sends a message, you can choose what to do.
        For now, we’ll just trigger an update broadcast.
        """
        data = json.loads(text_data)
        message = data.get("message", "update")
        self.send_updates(message)

    def chat_message(self, event):
        """
        Called when group_send sends a message.
        """
        self.send_updates(event["message"])

    def send_updates(self, message):
        """
        Collects 'next in line' students and sends them as JSON.
        """
        now_ph = localtime(timezone.now())
        today = now_ph.date()

        # Find current student
        get_current_number = StudentAppointments.objects.filter(
            status="current",
            datetime__date=today
        ).order_by("datetime").first()

        # Collect candidates in order
        priority_standby = StudentAppointments.objects.filter(
            status="standby", is_priority="yes", datetime__date=today
        ).order_by("datetime")

        regular_standby = StudentAppointments.objects.filter(
            status="standby", is_priority="no", datetime__date=today
        ).order_by("datetime")

        regular_pending = StudentAppointments.objects.filter(
            status="pending", is_priority="no", datetime__date=today
        ).order_by("datetime")

        candidates = list(priority_standby) + list(regular_standby) + list(regular_pending)
        next_in_line = candidates[:5]

        # Prepare JSON response
        payload = {
            "message": message,
            "current": {
                "idNumber": get_current_number.idNumber if get_current_number else None,
                "ticket_number": get_current_number.ticket_number if get_current_number else None,
                "firstName": get_current_number.firstName if get_current_number else None,
                "lastName": get_current_number.lastName if get_current_number else None,
                "status": get_current_number.status if get_current_number else None,
                "requestType": str(get_current_number.requestType) if get_current_number and get_current_number.requestType else None,
                "datetime": localtime(get_current_number.datetime).strftime("%H:%M")
                if get_current_number else None,
            } if get_current_number else None,
            "next_in_line": [
                {
                    "idNumber": s.idNumber,
                    "ticket_number": s.ticket_number,
                    "firstName": s.firstName,
                    "lastName": s.lastName,
                    "status": s.status,
                    "requestType": str(s.requestType) if s.requestType else None,
                    "datetime": localtime(s.datetime).strftime("%H:%M"),
                }
                for s in next_in_line
            ]
        }

        # Send to frontend
        self.send(text_data=json.dumps(payload))
