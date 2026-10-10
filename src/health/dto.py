from typing import Literal

from pydantic import BaseModel


class HealthDTO(BaseModel):
    status: Literal["ok", "unavailable"]
