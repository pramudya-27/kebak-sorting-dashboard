import asyncio
import websockets
import json

async def test():
    async with websockets.connect("ws://localhost:8000/ws/detections") as ws:
        msg = await ws.recv()
        data = json.loads(msg)
        print("Keys:", data.keys())
        for det in data.get('fused_detections', []):
            print("Det:", det.get('class_name'), "Has mask:", 'mask_polygons' in det)
            
asyncio.run(test())
