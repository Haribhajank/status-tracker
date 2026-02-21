import asyncio
import json
import os
import re
from datetime import datetime
from typing import List, Dict
from contextlib import asynccontextmanager

import aiohttp
import feedparser
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse

# We Define interval here
CHECK_INTERVAL = 60


@asynccontextmanager
async def lifespan(app: FastAPI):

    task = asyncio.create_task(engine.run())
    
    yield
    
    task.cancel()



app = FastAPI(lifespan=lifespan)



class StatusEngine:
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.providers = []
        self.last_seen = {}
        self.latest_updates = {}
        self.active_connections: List[WebSocket] = []

    def load_providers(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"error reading {self.config_file}: {e}")
        return self.providers

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

    async def fetch_feed(self, session, provider):
        async with session.get(provider["rss"], timeout=10) as response:
            text = await response.text()
            return await asyncio.to_thread(feedparser.parse, text)

    async def process_provider(self, session, provider):
        provider_name = provider["name"]
        try:
            feed = await self.fetch_feed(session, provider)

            for entry in feed.entries:
                published = datetime(*entry.published_parsed[:6])

                if (
                    provider_name in self.last_seen
                    and published <= self.last_seen[provider_name]
                ):
                    continue

                clean_time = published.isoformat().replace("T", " ")
                clean_summary = re.sub(r'<[^>]+>', ' ', entry.summary)
                clean_summary = " ".join(clean_summary.split())
                
                formatted_text = f"[{clean_time}] Product: {provider_name} - {entry.title}\n{clean_summary}\n"

                if provider_name not in self.latest_updates:
                    self.latest_updates[provider_name] = []
                self.latest_updates[provider_name].insert(0, formatted_text)

                if len(self.latest_updates[provider_name]) > 50:
                    self.latest_updates[provider_name].pop()

                print(formatted_text)

                await self.broadcast(formatted_text)

            if feed.entries:
                latest = feed.entries[0]
                self.last_seen[provider_name] = datetime(
                    *latest.published_parsed[:6]
                )

        except Exception as e:
            print(f"error processing {provider_name}: {e}")

    async def run(self):
        async with aiohttp.ClientSession() as session:
            while True:
                self.providers = self.load_providers()
                if self.providers:
                    tasks = [
                        self.process_provider(session, provider)
                        for provider in self.providers
                    ]
                    await asyncio.gather(*tasks)
                await asyncio.sleep(CHECK_INTERVAL)

engine = StatusEngine("providers.json")




@app.get("/", response_class=PlainTextResponse)
def get_status():
    if not engine.latest_updates:
        output = "waiting for updates..."
        print(f"api request: {output}")
        return output
        
    all_updates = []
    for provider_list in engine.latest_updates.values():
        all_updates.extend(provider_list)
        
    output = "\n".join(all_updates)
    
    print("\n--- SERVING API REQUEST ---")
    print(output)
    print("---------------------------\n")
    
    return output

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await engine.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        engine.disconnect(websocket)

######################## To genrate mock live events for testing to check on own setup #############################


# @app.get("/test-event")
# async def trigger_test_event():
#     now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     fake_message = f"[{now}] Product: System Test - Manual Trigger\nStatus: Investigating This is a simulated event to test the WebSocket connection.\n"
    
#     if "System Test" not in engine.latest_updates:
#         engine.latest_updates["System Test"] = []
#     engine.latest_updates["System Test"].insert(0, fake_message)
    
#     print(fake_message)
    
#     await engine.broadcast(fake_message)
    
#     return {"message": "Test event successfully broadcasted!"}