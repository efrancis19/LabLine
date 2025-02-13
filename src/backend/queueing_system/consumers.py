from channels.generic.websocket import AsyncWebsocketConsumer
import json


#This consumer ensures that updates 
# (e.g., request creation, status changes) 
# are pushed to the relevant users' dashboards in real time.

from channels.generic.websocket import AsyncWebsocketConsumer
import json


class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            self.user_id = self.scope["user"].id
            user_type = self.scope["user"].user_type

            if user_type == "tutor":
                self.group_name = "tutors_group"
            elif user_type == "lecturer":
                self.group_name = "lecturers_group"  # New group for lecturers
            else:
                self.group_name = f"user_{self.user_id}"

            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()


    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def update_dashboard(self, event):
        message = {
            "message": event.get("message"),
            "type": event.get("event_type"),
            "request_id": event.get("request_id"),
            "new_status": event.get("new_status"),
            "description": event.get("description"),
            "student": event.get("student"),
        }
        await self.send(text_data=json.dumps(message))
