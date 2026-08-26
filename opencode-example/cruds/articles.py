from typing import List
from sqlalchemy import select
from sqlalchemy.orm import Session
from database import Article, Tag

def get_article_id(
    db: Session,
    article_id: int 
):
    return db.get(Article, article_id)

def ajouter_tags(
    db: Session,
    article: Article,
    noms: List[str]
):
    """
    Ajoute les tags désignés par leur nom à l'article ; un tag inconnu est créé.
    Les changements sont écrits à la session (flush) mais pas validés (commit côté routeur).
    """
    for nom in noms:
        tag = db.execute(select(Tag).where(Tag.nom == nom)).scalar_one_or_none()
        if tag is None:
            tag = Tag(nom=nom)
            db.add(tag)
            db.flush()  # générer l'ID pour l'association à la table article-tag
        article.tags.append(tag)
    return article
