from fastapi import APIRouter, Path, Query, HTTPException, Depends
from schemas.auteurs import AuteurCreation, AuteurResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import get_db, Tag
from exceptions import RessourceNonTrouveException
from cruds.auteurs import get_auteur_id, get_auteur_by_tag

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

## IMPORTANT : la route `by_tag` est déclarée AVANT `/{auteur_id}`,
## car sinon FastAPI matcherait "by_tag" sur le paramètre d'ID et retournerait 422.
@router.get("/by_tag", response_model=AuteurResponse)
def get_auteur_by_tag_route(
    tag: str = Query(min_length=1, description="Nom du tag à rechercher"),
    db: Session = Depends(get_db),
):
    """Retourne l'auteur d'un article portant le tag donné (recherché par son nom).

    - plusieurs articles portent ce tag avec des auteurs différents :
      l'auteur au plus petit ID est retourné (comportement déterministe)
    - aucun article ne porte ce tag, ou le tag n'existe pas : 404 standard
    """
    auteur = get_auteur_by_tag(db, tag)
    if auteur is None:
        # identifier la ressource manquante : ID du tag s'il existe dans la base,
        # sinon son nom (aucun entier à fournir)
        tag_existant = db.execute(select(Tag).where(Tag.nom == tag)).scalar_one_or_none()
        identifiant = tag_existant.id if tag_existant is not None else tag
        raise RessourceNonTrouveException(
            id=identifiant,
            resource_type="auteur",
        )
    return auteur


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