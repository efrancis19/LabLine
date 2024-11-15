from channels.generic.websocket import AsyncWebsocketConsumer
import json
from collections import deque

active_tutors = deque()  # Stores channels of logged-in tutors

class StudentConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data['type'] == 'help_request':
            if active_tutors:
                # Get the next tutor in line and requeue them
                tutor_channel = active_tutors.popleft()
                await self.channel_layer.send(
                    tutor_channel,
                    {
                        'type': 'help.message',
                        'message': data['description'],
                        'pc_number': data['pc_number'],
                        'student_channel': self.channel_name
                    }
                )
                active_tutors.append(tutor_channel)
            else:
                await self.send(text_data=json.dumps({
                    'message': "No tutors available at the moment. Please try again later."
                }))

class TutorConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        active_tutors.append(self.channel_name)

    async def disconnect(self, close_code):
        # Remove tutor from active list on disconnect
        if self.channel_name in active_tutors:
            active_tutors.remove(self.channel_name)

    async def help_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'pc_number': event['pc_number']
        }))
