import json
from channels.generic.websocket import WebsocketConsumer

class TutorConsumer(WebsocketConsumer):
    def connect(self):
        # Add tutor to a group called 'tutors'
        self.accept()
        self.group_name = "tutors"
        self.channel_layer.group_add(self.group_name, self.channel_name)

    def disconnect(self, close_code):
        # Remove tutor from the group
        self.channel_layer.group_discard(self.group_name, self.channel_name)

    def receive(self, text_data):
        # No need to handle receiving data for this use case
        pass

    def notify_tutors(self, event):
        # Send message to WebSocket
        self.send(text_data=json.dumps({'message': event['message']}))
