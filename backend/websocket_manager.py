import asyncio
class WebsocketManager:
    def __init__(self): self.clients=set()
    async def broadcast(self,data):
        async def send(ws):
            try: await asyncio.wait_for(ws.send_json(data),2)
            except Exception: self.clients.discard(ws)
        await asyncio.gather(*(send(w) for w in list(self.clients)))
