# students/consumers.py
import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from personel.models import StudentAppointments
from django.utils import timezone
from django.utils.timezone import localtime
from personel.views import get_display_queue


class StudentsConsumer(WebsocketConsumer):
    def connect(self):
        # We'll just use a fixed group name (all live updates go here)
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
        For now, we'll just trigger an update broadcast.
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
        Collects data using the exact same logic as personel/views.py
        """
        now_ph = localtime(timezone.now())
        today = now_ph.date()

        # Auto-cancel expired skips (same as views.py)
        expired = StudentAppointments.objects.filter(
            status="skip", skip_until__lt=now_ph
        )
        for appt in expired:
            appt.status = "cancel"
            appt.save()

        # Get current student (same as views.py)
        get_current_number = StudentAppointments.objects.filter(
            status="current",
            datetime__date=today
        ).order_by("datetime").first()

        # Get served count (FIXED: should count "done" and "current", not "pending" and "standby")
        served_today = StudentAppointments.objects.filter(
            status__in=["done", "current"],
            datetime__date=today
        ).count()

        next_should_be_priority = (served_today % 3) == 2

        # Get next in line using the new function
        next_in_line_students = get_display_queue(today, limit=5)

        # Get additional data for display
        non_priority_students = StudentAppointments.objects.filter(
            is_priority="no",
            status="pending",
            datetime__date=today
        ).order_by("datetime")

        priority_students = StudentAppointments.objects.filter(
            is_priority="yes",
            status__in=["pending", "skip"],
            datetime__date=today
        ).order_by("datetime")

        skip_non_priority_students = StudentAppointments.objects.filter(
            is_priority="no",
            status="skip",
            datetime__date=today
        ).order_by("datetime")

        # Prepare JSON response
        payload = {
            "message": message,
            "current": {
                "id": get_current_number.id if get_current_number else None,
                "idNumber": get_current_number.idNumber if get_current_number else None,
                "ticket_number": get_current_number.ticket_number if get_current_number else None,
                "firstName": get_current_number.firstName if get_current_number else None,
                "lastName": get_current_number.lastName if get_current_number else None,
                "status": get_current_number.status if get_current_number else None,
                "is_priority": get_current_number.is_priority if get_current_number else None,
                "requestType": str(get_current_number.requestType) if get_current_number and get_current_number.requestType else None,
                "datetime": localtime(get_current_number.datetime).strftime("%H:%M")
                if get_current_number else None,
            } if get_current_number else None,
            # Send list of up to 5 students following the 2:1 pattern
            "next_in_line": [
                {
                    "id": s.id,
                    "idNumber": s.idNumber,
                    "ticket_number": s.ticket_number,
                    "firstName": s.firstName,
                    "lastName": s.lastName,
                    "status": s.status,
                    "is_priority": s.is_priority,
                    "requestType": str(s.requestType) if s.requestType else None,
                    "datetime": localtime(s.datetime).strftime("%H:%M"),
                }
                for s in next_in_line_students
            ],
            "next_should_be_priority": next_should_be_priority,
            "stats": {
                "served_today": served_today,
                "non_priority_count": non_priority_students.count(),
                "priority_count": priority_students.count(),
                "skip_count": skip_non_priority_students.count(),
            },
            "queue_data": {
                "non_priority_students": [
                    {
                        "id": s.id,
                        "ticket_number": s.ticket_number,
                        "firstName": s.firstName,
                        "lastName": s.lastName,
                        "status": s.status,
                        "datetime": localtime(s.datetime).strftime("%H:%M"),
                    }
                    for s in non_priority_students[:10]
                ],
                "priority_students": [
                    {
                        "id": s.id,
                        "ticket_number": s.ticket_number,
                        "firstName": s.firstName,
                        "lastName": s.lastName,
                        "status": s.status,
                        "datetime": localtime(s.datetime).strftime("%H:%M"),
                    }
                    for s in priority_students[:10]
                ],
                "skip_students": [
                    {
                        "id": s.id,
                        "ticket_number": s.ticket_number,
                        "firstName": s.firstName,
                        "lastName": s.lastName,
                        "status": s.status,
                        "datetime": localtime(s.datetime).strftime("%H:%M"),
                    }
                    for s in skip_non_priority_students[:10]
                ]
            }
        }

        # Send to frontend
        self.send(text_data=json.dumps(payload))