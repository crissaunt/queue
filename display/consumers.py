# display/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from personel.models import Appointments, QueueControl
from django.utils import timezone
from django.utils.timezone import localtime

class DisplayConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "students_live_updates"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        
        # Send initial data
        current_data = await self.get_current_display_data()
        await self.send(text_data=json.dumps({
            'type': 'display_update',
            'data': current_data,
            'source': 'initial_connection'
        }))
        print("✅ Display WebSocket connected and sent initial data")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        print("🔴 Display WebSocket disconnected")

    async def receive(self, text_data):
        # Handle refresh requests from client
        data = json.loads(text_data)
        if data.get('message') == 'update':
            current_data = await self.get_current_display_data()
            await self.send(text_data=json.dumps({
                'type': 'display_update', 
                'data': current_data,
                'source': 'manual_refresh'
            }))

    async def chat_message(self, event):
        message = event.get("message", "")

        if message == "queue_update":
            # ⚡ Send queue status only (faster)
            queue_status = await self.get_queue_status_only()

            await self.send(text_data=json.dumps({
                "type": "queue_status",
                "data": queue_status,
                "source": "queue_toggle"
            }))

        else:
            # Default: refresh current + queue
            current_data = await self.get_current_display_data()
            await self.send(text_data=json.dumps({
                "type": "display_update",
                "data": current_data,
                "source": "queue_change"
            }))


    @sync_to_async
    def get_current_display_data(self):
        """Get current student data for display including queue status"""
        try:
            # Auto-cancel outdated appointments
            Appointments.cancel_outdated()
            Appointments.cancel_expired_skips()

            # Use consistent date handling
            now_ph = localtime(timezone.now())
            today = now_ph.date()

            # Get current serving student
            current_student = Appointments.objects.filter(
                status="current",
                datetime__date=today
            ).order_by("datetime").first()

            # Get queue status
            queue_control = QueueControl.get_queue_control()
            queue_status = {
                'is_running': queue_control.is_running,
                'status_text': 'RUNNING' if queue_control.is_running else 'STOPPED'
            }

            if current_student:
                return {
                    "current": {
                        "id": current_student.id,
                        "ticket_number": current_student.ticket_number,
                        "firstName": current_student.firstName,
                        "lastName": current_student.lastName,
                        "status": current_student.status,
                        "is_priority": current_student.is_priority,
                        "user_type": current_student.user_type,
                        "skip_count": current_student.skip_count or 0,
                        "requestType": str(current_student.requestType) if current_student.requestType else current_student.custom_request or 'No Request',
                    },
                    "queue_status": queue_status
                }
            else:
                return {
                    "current": None,
                    "queue_status": queue_status
                }

        except Exception as e:
            print(f"❌ Error in get_current_display_data: {e}")
            import traceback
            traceback.print_exc()
            return {
                "current": None,
                "queue_status": {
                    'is_running': True,
                    'status_text': 'RUNNING'
                }
            }