import json
from channels.generic.websocket import AsyncWebsocketConsumer

class InterviewConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope["user"].id
        if self.user_id:
            self.group_name = f"interview_{self.user_id}"
            
            # Join user's personal group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def interview_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'message': event['message'],
            'interview_id': event['interview_id']
        }))
        
    async def evaluation_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'evaluation_result',
            'question_id': event['question_id'],
            'evaluation': event['evaluation']
        }))
