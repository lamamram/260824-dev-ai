from sqlalchemy.orm import Session
from database import Utilisateur

def get_auteur_id(
    db: Session,
    auteur_id: int 
):
    return db.get(Utilisateur, auteur_id)