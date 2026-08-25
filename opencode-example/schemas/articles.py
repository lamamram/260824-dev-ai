from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime

# ------------ pydantic requests schémas ------------
class ArticleCreation(BaseModel):
    titre: str = Field(min_length=3, max_length=200)
    contenu: str = Field(min_length=10)

class ArticleUpdate(BaseModel):
    titre: str = Field(min_length=3, max_length=200)
    contenu: str = Field(min_length=10)
    publie: Optional[bool] = Field(default=None, description="Indique si l'article est publié ou non. Si None, ne pas modifier le statut de publication.")

# ------------ pydantic responses schémas ------------

class TagSchema(BaseModel):
    id: int
    nom: str

class AuteurSchema(BaseModel):
    id: int
    username: str

class ArticleResponse(BaseModel):
    # pour convertir les objets SQLAlchemy en dictionnaires, on utilise la config from_attributes=True
    # semble être déprécié car les modèles Sqlalchemy sont convertis en dictionnaire dans la réponse
    # model_config = ConfigDict(from_attributes=True)
    id: int
    titre: str
    contenu: str
    publie: bool = False
    created_at: datetime
    # on utilise un schéma imbriqué pour l'auteur et les tags
    auteur: AuteurSchema          # Relation imbriquée
    tags: List[TagSchema] = []    # Liste de tag

class ArticleCountByUser(BaseModel):
    username: str
    nb_articles: int

class ArticleCountPublieByUser(BaseModel):
    username: str
    publies: int
    brouillons: int