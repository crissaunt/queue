import json
from channels.generic.websocket import AsyncWebsocketConsumer

class SurveyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(
            "survey_updates",
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            "survey_updates",
            self.channel_name
        )

    async def survey_update(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'surveys': event['surveys']
        }))