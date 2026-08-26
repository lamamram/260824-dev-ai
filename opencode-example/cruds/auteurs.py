from sqlalchemy import select
from sqlalchemy.orm import Session
from database import Utilisateur, Tag, Article, articles_tags

def get_auteur_id(
    db: Session,
    auteur_id: int 
):
    return db.get(Utilisateur, auteur_id)

def get_auteur_by_tag(
    db: Session,
    tag_nom: str
):
    """Retourne l'auteur d'un article portant le tag donné (recherché par son nom).

    Comportements :
    - aucun article ne porte ce tag, ou le tag n'existe pas : retourne ``None``
    - plusieurs articles portent ce tag avec des auteurs différents :
      retourne l'auteur au plus petit ``Utilisateur.id`` (ordonnance déterministe)
    """
    requete = (
        select(Utilisateur)
        .join(Article, Article.auteur_id == Utilisateur.id)
        .join(articles_tags, articles_tags.c.article_id == Article.id)
        .join(Tag, Tag.id == articles_tags.c.tag_id)
        .where(Tag.nom == tag_nom)
        .order_by(Utilisateur.id)
    )
    return db.execute(requete).scalars().first()
