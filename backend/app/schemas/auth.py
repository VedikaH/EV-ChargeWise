from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    role: Optional[str] = None #remove optional later afte rtesting  

class TokenData(BaseModel):
    id: int
    role: str
    exp: datetime

    class Config:
        from_attributes = True