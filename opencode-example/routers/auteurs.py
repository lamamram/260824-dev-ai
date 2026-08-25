from fastapi import APIRouter, Path, Query, HTTPException, Depends
from schemas.auteurs import AuteurCreation, AuteurResponse
from sqlalchemy.orm import Session
from database import get_db
from exceptions import RessourceNonTrouveException
from cruds.auteurs import get_auteur_id

router = APIRouter(prefix="/auteurs", tags=["Auteurs"])

@router.get("/")
def list_auteurs(
    page: int = Query(1, gt=0, description="Numéro de la page (doit être un entier positif)"),
    taille: int = Query(10, gt=0, le=100, description="Nombre d'auteurs par page (doit être un entier positif entre 1 et 100)")
):
    return {
        "page": page,
        "taille": taille,
        "auteurs": [],
    }

@router.post("/", response_model=AuteurResponse, status_code=201)
def create_auteur(auteur: AuteurCreation):
    """
    Crée un nouvel auteur.
    """
    return {
        "id": 1, **auteur.model_dump()  # Retourne l'auteur créé avec un ID fictif
    }

## route pour récupérer un auteur
## avec le schéma de réponse
## la session SqlAlchemy
@router.get("/{auteur_id}", response_model=AuteurResponse)
def get_auteur(
    auteur_id: int = Path(gt=0, description="L'ID de l'auteur doit être un entier positif"),
    db: Session = Depends(get_db)
):
    """Retourne un auteur fictif identifié par son ID entier."""
    auteur = get_auteur_id(db, auteur_id)
    if auteur is None:
        raise RessourceNonTrouveException(
            id=auteur_id, 
            resource_type="auteur"
        )
    
    return auteur