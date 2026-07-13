"""
WebSocket consumer for real-time notifications.

Each authenticated user joins a personal group: notifications_user_{id}
The Celery task pushes messages to this group via the channel layer.
"""
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class NotificationConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        user = self.scope["user"]
        if user.is_anonymous:
            await self.close()
            return

        # Each user gets their own notification group
        self.group_name = f"notifications_user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_notification(self, event):
        """
        Handler for messages sent to the group via:
            channel_layer.group_send(group, {"type": "send_notification", ...})

        The 'type' field maps to this method name (dots/hyphens → underscores).
        """
        await self.send_json(event["data"])
