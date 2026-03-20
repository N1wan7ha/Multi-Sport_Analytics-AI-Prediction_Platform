"""WebSocket consumers for live prediction updates."""

import json

from channels.generic.websocket import AsyncWebsocketConsumer


class LivePredictionConsumer(AsyncWebsocketConsumer):
	async def connect(self):
		match_id = self.scope['url_route']['kwargs'].get('match_id')
		if not match_id:
			await self.close(code=4001)
			return

		self.group_name = f'prediction_match_{match_id}'
		await self.channel_layer.group_add(self.group_name, self.channel_name)
		await self.accept()

	async def disconnect(self, close_code):
		if hasattr(self, 'group_name'):
			await self.channel_layer.group_discard(self.group_name, self.channel_name)

	async def prediction_update(self, event):
		await self.send(text_data=json.dumps(event.get('payload', {})))