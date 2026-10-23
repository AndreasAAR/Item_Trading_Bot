import time
import requests
from typing import List, Optional
from config.settings import TRADERA_PROFILE_URL, USER_AGENT
from src.tradera.parser import TraderaParser
from src.tradera.models import TraderaItemCard, TraderaItemDetail

class TraderaClient:
    def __init__(self, user_agent: str = USER_AGENT):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "sv,en;q=0.9",
        })

    def get_profile_items(self, profile_url: str = TRADERA_PROFILE_URL) -> List[TraderaItemCard]:
        """Fetches active items listed on the seller's profile."""
        response = self.session.get(profile_url, timeout=20)
        response.raise_for_status()
        return TraderaParser.parse_profile_page(response.text, base_url=profile_url)

    def get_item_detail(self, item_url: str, delay_seconds: float = 0.5) -> TraderaItemDetail:
        """Fetches full item details for a specific listing."""
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        response = self.session.get(item_url, timeout=20)
        response.raise_for_status()
        return TraderaParser.parse_item_page(response.text, item_url=item_url)
