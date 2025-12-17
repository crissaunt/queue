# personel/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import Appointments, QueueControl
from django.utils import timezone
from django.db.models import Case, When, Value, IntegerField
from django.utils.timezone import localtime

class QueueConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Join BOTH groups to receive updates from students AND personnel
        await self.channel_layer.group_add("queue_updates", self.channel_name)
        await self.channel_layer.group_add("students_live_updates", self.channel_name)
        await self.accept()
        
        # Send COMPLETE initial data when client connects
        complete_data = await self.get_complete_queue_data()
        await self.send(text_data=json.dumps({
            'type': 'full_update',
            'data': complete_data,
            'source': 'initial_connection'
        }))
        print(f"✅ Personnel WebSocket connected to both groups and sent COMPLETE data")

    async def disconnect(self, close_code):
        # Leave both groups
        await self.channel_layer.group_discard("queue_updates", self.channel_name)
        await self.channel_layer.group_discard("students_live_updates", self.channel_name)
        print("🔴 Personnel WebSocket disconnected from both groups")

    async def receive(self, text_data):
        # Handle messages from client if needed
        data = json.loads(text_data)
        if data.get('type') == 'get_full_data':
            complete_data = await self.get_complete_queue_data()
            await self.send(text_data=json.dumps({
                'type': 'full_update',
                'data': complete_data,
                'source': 'client_request'
            }))

    async def queue_update(self, event):
        """
        Handle updates from personnel actions
        """
        print("🔄 Full update triggered by personnel action")
        complete_data = await self.get_complete_queue_data()
        await self.send(text_data=json.dumps({
            'type': 'full_update',
            'data': complete_data,
            'source': 'personnel_action'
        }))

    async def chat_message(self, event):
        """
        Handle updates from student submissions
        """
        message_type = event.get('message', 'update')
        print(f"🎓 Full update triggered by student submission: {message_type}")
        
        complete_data = await self.get_complete_queue_data()
        await self.send(text_data=json.dumps({
            'type': 'full_update',
            'data': complete_data,
            'source': 'student_submission'
        }))

    @sync_to_async
    def get_complete_queue_data(self):
        # Auto-cancel outdated appointments (from previous days)
        outdated_count = Appointments.cancel_outdated()
        
        # Auto-cancel expired skips
        Appointments.cancel_expired_skips()

        """Get COMPLETE queue data for ALL sections with CONSISTENT date handling"""
        try:
            # Use the SAME date logic as the views - Django's built-in timezone
            now_ph = localtime(timezone.now())
            today = now_ph.date()
            
            print(f"🔍 CONSUMER DEBUG (Consistent Date):")
            print(f"   - Today's date: {today}")
            print(f"   - Current time: {now_ph}")
            
            # Get queue status
            queue_control = QueueControl.get_queue_control()
            is_queue_running = queue_control.is_running
            print(f"   - Queue status: {'RUNNING' if is_queue_running else 'STOPPED'}")
            
            # 1) Get ALL students in the queue (standby + non-priority pending)
            all_queue_students = []
            
            # First add ALL standby students
            standby_students = list(
                Appointments.objects.filter(
                    status="standby",
                    datetime__date=today
                ).order_by("datetime")
            )
            print(f"   - Standby students: {len(standby_students)}")
            all_queue_students.extend(standby_students)
            
            # Then add ALL non-priority pending students
            non_priority_students = list(
                Appointments.objects.filter(
                    status="pending",
                    is_priority="no",
                    datetime__date=today
                ).order_by("datetime")
            )
            print(f"   - Non-priority pending: {len(non_priority_students)}")
            all_queue_students.extend(non_priority_students)
            
            print(f"   - Total queue students: {len(all_queue_students)}")
            
            # Build the next_queue_list for WebSocket (first 5 for sidebar)
            next_queue_list = []
            for queue_item in all_queue_students[:5]:  # First 5 for sidebar
                next_queue_list.append({
                    'ticket_number': queue_item.ticket_number,
                })

            # FIXED: Build FULL queue list for modal (students beyond the first 5)
            full_queue_list = []
            # Get ALL students starting from index 5 (student #6 and beyond)
            for queue_item in all_queue_students[5:]:  
                full_queue_list.append({
                    'ticket_number': queue_item.ticket_number,
                })

            print(f"   - Next queue (sidebar): {len(next_queue_list)} items")
            print(f"   - Full queue (modal): {len(full_queue_list)} items")

            # 2) Priority Queue (all priority students)
            priority_students = list(
                Appointments.objects.filter(
                    is_priority="yes",
                    status__in=["pending", "skip"],
                    datetime__date=today
                ).annotate(
                    status_order=Case(
                        When(status="pending", then=Value(1)),
                        When(status="skip", then=Value(2)),
                        default=Value(5),
                        output_field=IntegerField(),
                    )
                ).order_by("status_order", "datetime")
            )

            priority_queue_list = []
            for student in priority_students:
                priority_queue_list.append({
                    'id': student.id,
                    'ticket_number': student.ticket_number,
                    'firstName': student.firstName,
                    'middleName': student.middleName or '',
                    'lastName': student.lastName,
                    'status': student.status,
                })

            # 3) Skipped List (non-priority skipped)
            skipped_students = list(
                Appointments.objects.filter(
                    is_priority="no",
                    status="skip",
                    datetime__date=today
                ).order_by("datetime")
            )

            skipped_list = []
            for student in skipped_students:
                skipped_list.append({
                    'id': student.id,
                    'ticket_number': student.ticket_number,
                    'firstName': student.firstName,
                    'middleName': student.middleName or '',
                    'lastName': student.lastName,
                })

            # 4) Current serving student
            current_student = Appointments.objects.filter(
                status="current",
                datetime__date=today
            ).order_by("datetime").first()

            print(f"   - Current student query result: {current_student}")
            if current_student:
                print(f"   - Current student details:")
                print(f"     - Ticket: {current_student.ticket_number}")
                print(f"     - Status: {current_student.status}")
                
                current_data = {
                    'id': current_student.id,
                    'ticket_number': current_student.ticket_number,
                    'firstName': current_student.firstName,
                    'middleName': current_student.middleName or '',
                    'lastName': current_student.lastName,
                    'courses': str(current_student.courses) if current_student.courses else '',
                    'requestType': str(current_student.requestType) if current_student.requestType else current_student.custom_request or 'No Request',
                }
            else:
                print(f"   - No current student found for date: {today}")
                current_data = None

            # Build complete payload - INCLUDES QUEUE STATUS
            complete_data = {
                'next_queue': next_queue_list,
                'full_queue': full_queue_list,
                'priority_queue': priority_queue_list,
                'skipped_list': skipped_list,
                'current_student': current_data,
                'queue_status': {
                    'is_running': is_queue_running,
                    'status_text': 'RUNNING' if is_queue_running else 'STOPPED'
                }
            }

            print(f"📊 Complete data prepared:")
            print(f"   - Next queue: {len(next_queue_list)} items")
            print(f"   - Full queue: {len(full_queue_list)} items") 
            print(f"   - Priority: {len(priority_queue_list)} items")
            print(f"   - Skipped: {len(skipped_list)} items")
            print(f"   - Current: {'Yes' if current_data else 'No'}")
            print(f"   - Queue running: {is_queue_running}")

            return complete_data

        except Exception as e:
            print(f"❌ Error in get_complete_queue_data: {e}")
            import traceback
            traceback.print_exc()
            return {
                'next_queue': [],
                'full_queue': [],
                'priority_queue': [],
                'skipped_list': [],
                'current_student': None,
                'queue_status': {
                    'is_running': True,
                    'status_text': 'RUNNING'
                }
            }