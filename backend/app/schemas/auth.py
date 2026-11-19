"""Modèles Pydantic de l'authentification (entrée / sortie)."""
from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=254)  # l'email de l'utilisateur
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    email: str
    name: str | None = None
    role: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # secondes
    user: UserOut
