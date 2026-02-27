# backend\app\schemas\response_schema.py

from typing import Optional,Any
from pydantic import BaseModel

class ResponseSchema(BaseModel):
    status: bool
    message : str
    data: Optional[Any] = None
