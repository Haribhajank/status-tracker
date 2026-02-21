import re
import asyncio
import aiohttp
import feedparser
from datetime import datetime
from fastapi import FastAPI
from typing import Dict, List

app = FastAPI(title="Multi-Provider Status Tracker")

PROVIDERS = [
    {"name": "OpenAI", "rss": "https://status.openai.com/history.rss"},
    # Add more providers here
]

CHECK_INTERVAL = 60


class StatusEngine:
    def __init__(self, providers: List[Dict]):
        self.providers = providers
        self.last_seen = {}
        self.latest_updates = {}

    async def fetch_feed(self, session, provider):
        async with session.get(provider["rss"], timeout=10) as response:
            text = await response.text()
            return feedparser.parse(text)

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

                update = {
                    "provider": provider_name,
                    "title": entry.title,
                    "summary": entry.summary,
                    "time": published.isoformat(),
                }

                self.latest_updates[provider_name] = update
                formatted_time = update["time"].replace("T", " ")

                clean_summary = re.sub(r'<br\s*/?>', ' ', update["summary"])
                clean_summary = re.sub(r'<[^>]+>', '', clean_summary).strip()

                print(f"[{formatted_time}] Product: {update['provider']} - {update['title']}")
                print(f"{clean_summary}\n")

            if feed.entries:
                latest = feed.entries[0]
                self.last_seen[provider_name] = datetime(
                    *latest.published_parsed[:6]
                )

        except Exception as e:
            print(f"Error processing {provider_name}: {e}")

    async def run(self):
        async with aiohttp.ClientSession() as session:
            while True:
                tasks = [
                    self.process_provider(session, provider)
                    for provider in self.providers
                ]
                await asyncio.gather(*tasks)
                await asyncio.sleep(CHECK_INTERVAL)


engine = StatusEngine(PROVIDERS)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(engine.run())


@app.get("/")
def get_status():
    return engine.latest_updates


@app.get("/health")
def health():
    return {"status": "running"}