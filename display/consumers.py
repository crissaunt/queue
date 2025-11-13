# students/consumers.py
import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from personel.models import Appointments

class DisplayConsumer(WebsocketConsumer):
    def connect(self):
        self.group_name = "students_live_updates"
        async_to_sync(self.channel_layer.group_add)(self.group_name, self.channel_name)
        self.accept()
        self.send_updates("Connected")

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(self.group_name, self.channel_name)

    def send_updates(self, message):
        # Auto-cancel outdated appointments (from previous days)
        outdated_count = Appointments.cancel_outdated()
        
        # Auto-cancel expired skips
        Appointments.cancel_expired_skips()
        
        # Get current student (automatically from today only)
        get_current_number = Appointments.get_current_student()

        # Build payload
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
            } if get_current_number else None,
            "outdated_cancelled": outdated_count
        }

        self.send(text_data=json.dumps(payload))