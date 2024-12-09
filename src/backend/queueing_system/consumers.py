from channels.generic.websocket import AsyncWebsocketConsumer
import json


#This consumer ensures that updates 
# (e.g., request creation, status changes) 
# are pushed to the relevant users' dashboards in real time.


class DashboardConsumer(AsyncWebsocketConsumer): 
    async def connect(self):
        # Getting the user ID from the URL or session
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            self.user_id = self.scope["user"].id
            self.group_name = f"user_{self.user_id}"
            
            # Adding the user to their own group
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        # Removing the user from their group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Receiving messages from group and send to WebSocket
    async def update_dashboard(self, event):
        # Preparing the message payload
        message = {
            "message": event.get("message"),
            "type": event.get("event_type"),
            "request_id": event.get("request_id"),
            "new_status": event.get("new_status"),
            "description": event.get("description"),
            "student": event.get("student"),
        }
        await self.send(text_data=json.dumps(message))
