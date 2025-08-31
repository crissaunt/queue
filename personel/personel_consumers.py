import json
from channels.generic.websocket import AsyncWebsocketConsumer

class QueueConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("queue", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("queue", self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        # you can listen for custom client requests here if needed
        # for now, we just ignore incoming

    async def send_update(self, event):
        """
        Called when group_send("queue", {...}) is triggered
        """
        await self.send(text_data=json.dumps(event["data"]))
