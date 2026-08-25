from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime

# ------------ pydantic requests schémas ------------

class AuteurCreation(BaseModel):
    nom: str = Field(min_length=2, max_length=100)
    email: EmailStr
    age: int = Field(ge=18, le=120)
    tags: List[str] = Field(default_factory=list)
    biographie: Optional[str] = Field(default="", max_length=2000)

# ------------ pydantic responses schémas ------------

class TagSchema(BaseModel):
    id: int
    nom: str

class ProfileSchema(BaseModel):
    id: int
    bio: str
    avatar_url: str

class AuteurResponse(BaseModel):
    id: int
    username: str = Field(min_length=2, max_length=100)
    email: EmailStr                                    # Valide le format email
    active: bool
    is_admin: bool
    created_at: datetime
    tags: List[TagSchema] = []     # Liste vide par défaut à la place de [""]
    profil: ProfileSchema
