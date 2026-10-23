from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class TraderaItemCard(BaseModel):
    item_id: str
    title: str
    url: str
    thumbnail_url: Optional[str] = None
    leading_bid: Optional[int] = None
    starting_price: Optional[int] = None
    buy_now_price: Optional[int] = None
    item_type: Optional[str] = None
    ending_time: Optional[str] = None
    category_id: Optional[str] = None

class TraderaItemDetail(BaseModel):
    item_id: str
    title: str
    url: str
    description: str
    images: List[str] = Field(default_factory=list)
    buy_now_price: Optional[int] = None
    starting_price: Optional[int] = None
    leading_bid: Optional[int] = None
    attributes: Dict[str, str] = Field(default_factory=dict)
    shipping_cost: Optional[int] = None
    shipping_provider: Optional[str] = None
    pickup_available: bool = False
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def target_blocket_price(self) -> int:
        """Köp nu price if present, fallback to starting bid, or leading bid."""
        if self.buy_now_price is not None and self.buy_now_price > 0:
            return self.buy_now_price
        if self.starting_price is not None and self.starting_price > 0:
            return self.starting_price
        if self.leading_bid is not None and self.leading_bid > 0:
            return self.leading_bid
        return 0
