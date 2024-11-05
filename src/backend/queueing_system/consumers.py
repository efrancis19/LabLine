import json
from channels.generic.websocket import AsyncWebsocketConsumer

class StudentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "tutors_group"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        if text_data_json['type'] == 'help_request':
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'tutor_alert',
                    'message': f"Student needs help at PC {text_data_json['pc_number']}: {text_data_json['description']}"
                }
            )

class TutorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "tutors_group"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def tutor_alert(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'help_response',
            'message': message
        }))
