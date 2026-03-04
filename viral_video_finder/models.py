from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class Video:
    url: str
    title: str
    author: str
    views: int
    likes: int
    shares: int
    comments: int
    engagement_rate: float
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None

    def to_dict(self):
        return asdict(self)
