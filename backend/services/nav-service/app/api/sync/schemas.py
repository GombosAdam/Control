from pydantic import BaseModel
from typing import Optional


class SyncStartRequest(BaseModel):
    config_id: str
    date_from: str  # YYYY-MM-DD
    date_to: str    # YYYY-MM-DD
