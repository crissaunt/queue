# students/consumers.py
import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from personel.models import Appointments
from django.utils import timezone
from django.utils.timezone import localtime
from personel.views import get_display_queue
from django.db.models import Case, When, Value, IntegerField

class StudentsConsumer(WebsocketConsumer):
    def connect(self):
        self.group_name = "students_live_updates"
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()

        # Send initial data immediately
        self.send_full_update("initial_connection")
        print("✅ Student WebSocket connected")

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)
        print("🔴 Student WebSocket disconnected")

    def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get("type", "update")
        
        if message_type == "get_initial_data":
            self.send_full_update("initial_data_request")
        else:
            self.send_full_update(message_type)

    def chat_message(self, event):
        message_type = event.get("message", "update")
        print(f"🔄 Student consumer received chat_message: {message_type}")
        self.send_full_update(message_type)

    def send_full_update(self, source):
        try:
            now_ph = localtime(timezone.now())
            today = now_ph.date()
            print(f"🔍 Student consumer fetching data for date: {today}")

            # Auto-cancel expired skips
            expired = Appointments.objects.filter(
                status="skip", skip_until__lt=now_ph
            )
            for appt in expired:
                appt.status = "cancel"
                appt.save()

            # Current student
            get_current_number = Appointments.objects.filter(
                status="current",
                datetime__date=today
            ).order_by("datetime").first()

            # Served count (done + current)
            served_today = Appointments.objects.filter(
                status__in=["done", "current"],
                datetime__date=today
            ).count()

            # Determine 2:1 serving order
            next_should_be_priority = (served_today % 3) == 2

            # Unified queue function (2:1 applied)
            next_in_line_students = get_display_queue(today, limit=5)

            # Priority students
            priority_students = Appointments.objects.filter(
                is_priority="yes",
                status__in=["pending", "skip"],
                datetime__date=today
            ).annotate(
                status_order=Case(
                    When(status="pending", then=Value(1)),
                    When(status="skip", then=Value(2)),
                    default=Value(3),
                    output_field=IntegerField(),
                )
            ).order_by("status_order", "datetime")

            # Skipped non-priority students
            skip_non_priority_students = Appointments.objects.filter(
                is_priority="no",
                status="skip",
                datetime__date=today
            ).order_by("datetime")

            # Build payload with CORRECT field names that match frontend expectations
            payload = {
                "type": "full_update",
                "data": {
                    "current_student": {
                        "id": get_current_number.id if get_current_number else None,
                        "ticket_number": get_current_number.ticket_number if get_current_number else None,
                        "firstName": get_current_number.firstName if get_current_number else None,
                        "middleName": get_current_number.middleName if get_current_number else None,
                        "lastName": get_current_number.lastName if get_current_number else None,
                        "status": get_current_number.status if get_current_number else None,
                        "is_priority": get_current_number.is_priority if get_current_number else None,
                        "requestType": str(get_current_number.requestType) if get_current_number and get_current_number.requestType else None,
                        "custom_request": get_current_number.custom_request if get_current_number else None,
                        "courses": get_current_number.courses if get_current_number else None,
                        "student_id": get_current_number.student_id if get_current_number else None,
                        "datetime": localtime(get_current_number.datetime).strftime("%H:%M")
                        if get_current_number else None,
                    } if get_current_number else None,
                    "next_queue": [
                        {
                            "id": s.id,
                            "ticket_number": s.ticket_number,
                        }
                        for s in next_in_line_students
                    ],
                    "priority_queue": [
                        {
                            "id": s.id,
                            "ticket_number": s.ticket_number,
                            "firstName": s.firstName,
                            "middleName": s.middleName,
                            "lastName": s.lastName,
                            "status": s.status,
                            "datetime": localtime(s.datetime).strftime("%H:%M"),
                        }
                        for s in priority_students[:10]
                    ],
                    "skipped_list": [
                        {
                            "id": s.id,
                            "ticket_number": s.ticket_number,
                            "firstName": s.firstName,
                            "middleName": s.middleName,
                            "lastName": s.lastName,
                            "status": s.status,
                            "datetime": localtime(s.datetime).strftime("%H:%M"),
                        }
                        for s in skip_non_priority_students[:10]
                    ]
                },
                "next_should_be_priority": next_should_be_priority,
                "stats": {
                    "served_today": served_today,
                    "priority_count": priority_students.count(),
                    "skip_count": skip_non_priority_students.count(),
                },
                "source": source
            }

            # Send to frontend
            self.send(text_data=json.dumps(payload))
            print(f"✅ Student consumer sent full_update with source: {source}")

        except Exception as e:
            print(f"❌ Error in student consumer send_full_update: {e}")