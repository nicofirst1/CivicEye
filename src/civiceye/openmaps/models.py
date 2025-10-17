from dataclasses import dataclass
from typing import Optional


@dataclass
class AddressCandidate:
    """Represents a single candidate address returned by OpenStreetMap."""

    id: str
    street: str
    city: Optional[str]
    lat: float
    lon: float
    map_url: str
    map_provider: str
    map_image: Optional[bytes]
    similarity: Optional[float] = None
    map_error: Optional[str] = None
