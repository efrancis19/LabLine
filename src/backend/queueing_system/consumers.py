from channels.generic.websocket import AsyncWebsocketConsumer
import json
from queueing_system.core.state import ONLINE_TUTORS




class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            self.user_id = self.scope["user"].id
            user_type = self.scope["user"].user_type

            if user_type == "tutor":
                self.group_name = f"tutor_{self.user_id}"
                if self.user_id not in ONLINE_TUTORS:
                    ONLINE_TUTORS.append(self.user_id)

            elif user_type == "lecturer":
                self.group_name = "lecturers_group"
            else:
                self.group_name = f"user_{self.user_id}"

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        # Ensure that group_name is available before trying to remove from group
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        
        # Remove tutor from list if they disconnect
        if hasattr(self, 'user_id') and self.user_id in ONLINE_TUTORS:
            ONLINE_TUTORS.remove(self.user_id)

    async def update_dashboard(self, event):
        message = {
            "message": event.get("message"),
            "type": event.get("event_type"),
            "request_id": event.get("request_id"),
            "new_status": event.get("new_status"),
            "description": event.get("description"),
            "student": event.get("student"),
            "queue_position": event.get("queue_position"),
            "pc_number": event.get("pc_number"),
            "lab_id": event.get("lab_id"),
            "estimated_wait_time": event.get("estimated_wait_time"),
            "waiting_minutes": event.get("waiting_minutes"),
        }
        await self.send(text_data=json.dumps(message))

# Consumer to handle updates to the lab maps when students login and send requests.
class LabConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['user'].id
        self.group_name = f"user_{self.user_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def update_pc_status(self, event):
        pc_number = event['pc_number']
        status = event['status']  # red for when a students has pending requests and green when they do not.

        # Send the message to the WebSocket client (browser)
        await self.send(text_data=json.dumps({
            'pc_number': pc_number,
            'status': status,
        }))