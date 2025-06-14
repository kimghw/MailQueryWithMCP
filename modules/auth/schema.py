from pydantic import BaseModel, Field

class TokenData(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    scope: str
    token_type: str

class AuthCallback(BaseModel):
    code: str
    state: str
    session_state: str
