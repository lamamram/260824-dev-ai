from fastapi import APIRouter, Path, Query, HTTPException, Depends, BackgroundTasks
from datetime import datetime
from exceptions import RessourceNonTrouveException
from dependencies import get_query_params, GetQueryParams
from schemas.articles import ArticleCreation, ArticleResponse, ArticleUpdate, ArticleCountByUser, ArticleCountPublieByUser

# isoler les requêtes SQL dans un module cruds/articles.py pour séparer la logique métier de la logique de persistance
from cruds.articles import get_article_id
from typing import List

from sqlalchemy import select, func, case
from sqlalchemy.orm import Session, joinedload, selectinload
from database import get_db, Article, Utilisateur

router = APIRouter(prefix="/articles", tags=["Articles"])

## hooks
def envoyer_email_confirmation(destinataire: str, titre_article: str):
    """Fonction exécutée en arrière-plan après la réponse."""
    # Simulation d'un envoi email (en production : utiliser une bibliothèque async)
    print(f"Email envoyé à {destinataire} : article '{titre_article}' créé avec succès")

## routes

@router.get("/count_publie_by_user", response_model=List[ArticleCountPublieByUser])
def count_articles_publie(
    db: Session = Depends(get_db)
):
    stmt = (
        select(
            Utilisateur.username,
            func.count(case((Article.publie == True, 1))).label("publies"),
            func.count(case((Article.publie == False, 1))).label("brouillons"),
        )
        .join(Article, Article.auteur_id == Utilisateur.id)
        .group_by(Utilisateur.username)
        .having(func.count(Article.id) > 0)
        .order_by(func.count(Article.id).desc())
    )
    objects = db.execute(stmt).all()
    return objects

@router.get("/count_by_user", response_model=List[ArticleCountByUser])
def count_articles(
    db: Session = Depends(get_db)
):
    """Retourne le nombre d'articles par auteur dans la base de données."""

    ## nb d'articles par utilisateur avec select imbriqués
    # SELECT utilisateurs.*, (
        # SELECT count(articles.id) AS count_1 
        # FROM articles 
        # WHERE articles.auteur_id = utilisateurs.id
    # ) AS nb_articles 
    # FROM utilisateurs
    
    nb_articles_subq = (
        select(func.count(Article.id))
        .where(Article.auteur_id == Utilisateur.id)
        .scalar_subquery()
    )
    # 2 parties indépendantes: une colonne de modèle  , et une colonne calculée
    stmt = select(Utilisateur.username, nb_articles_subq.label("nb_articles"))

    # ici on utilise pas .scalars() ou .scalar() car le select n'est pas qu'un simple modèle
    # .all() seul gère le tuple (Utilisateur, nb_articles)
    objects = db.execute(stmt).all()
    
    ## transformation artisanale des tuples en dictionnaires pour la réponse JSON
    # objects = list(map(lambda obj: {
    #     "username": obj.username, 
    #     "nb_articles": obj.nb_articles
    # }, objects))
    # print(objects)
    # OU schéma de sortie Pydantic ArticleCountByUser

    return objects


@router.get("/", response_model=List[ArticleResponse])
def list_articles(
    params: dict = Depends(get_query_params),
    db: Session = Depends(get_db)
):
    auteur_id=2
    # page1 == offset=0, limit=10
    # page2 == offset=10, limit=10
    # (page_num - 1) * limit
    offset, limit = (params["page"] - 1) * params["taille"], params["taille"]
    
    ## REM 1: requête générée SELECT * FROM articles OFFSET 0 LIMIT 10
    
    ## REM 2: scenario lazy loading: par défaut sqlAlchemy ne s'intéresse qu'aux champs de la table article
    ## SAUF si les relations sont configurées avec lazy="joined" ou lazy="selectin" dans le modèle Article,
    articles = db.execute(
        select(Article
        ).where(Article.auteur_id == auteur_id
        ).offset(offset
        ).limit(limit)
    ).scalars().all()
    
    # quand on retourne les articles, les valeurs des relations (tags, auteur) ne sont pas encore chargées, 
    # elles seront chargées à la demande (lazy loading) quand on y accède dans le modèle Pydantic ArticleResponse
    # ==> 3 requêtes SQL en tout: 1 pour les articles, 1 pour l'auteur, 1 pour les tags
    # ou 2 en cas de relations préconfigurées

    ## REM 3: scenario eager loading: on charge les relations en même temps que l'article,
    # articles = db.execute(
    #     select(Article
    #     ).where(Article.auteur_id == auteur_id
    #     ).options(
    #         joinedload(Article.auteur),
    #         selectinload(Article.tags),
    #     ).offset(offset
    #     ).limit(limit)
    # ).scalars().all()
    # 2 requêtes SQL: une join pour utilisateur (many-to-one) et une where in pour tags (many-to-many)

    return articles

@router.post("/", status_code=201, response_model=ArticleResponse)
def create_article(
    req_article: ArticleCreation,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Reçoit un corps JSON :
    {"titre": "Mon article", "contenu": "...", "publie": false}
    """
    new_article = Article(
        titre=req_article.titre,
        contenu=req_article.contenu,
        auteur_id=1  # pour l'instant, on met un auteur fictif
    )
    # insérer l'article dans la base de données
    db.add(new_article)
    # pas besoin de flusher car db.commit() va flusher automatiquement
    db.commit()

    # ne sera exécuté qu'après la réponse HTTP, en arrière-plan, pour ne pas bloquer le client
    background_tasks.add_task(
        envoyer_email_confirmation,
        destinataire=new_article.auteur.email,
        titre_article=new_article.titre,
    )

    return new_article


@router.get("/{article_id}", response_model=ArticleResponse)
def get_article(
    article_id: int = Path(gt=0, description="L'ID de l'article doit être un entier positif"),
    db: Session = Depends(get_db)
):
    """Retourne un article fictif identifié par son ID entier."""
    article = get_article(db, article_id)
    if article is None:
        raise RessourceNonTrouveException(
            id=article_id, 
            resource_type="article"
        )
    
    return article

@router.delete("/{article_id}", status_code=204)
def delete_article(
    article_id: int = Path(gt=0, description="L'ID de l'article doit être un entier positif"),
    db: Session = Depends(get_db)
):
    """Supprime un article fictif identifié par son ID entier."""
    article = db.get(Article, article_id)
    if article is None:
        raise RessourceNonTrouveException(
            id=article_id, 
            resource_type="article"
        )
    db.delete(article) 
    db.commit()
    return None

@router.put("/{article_id}", response_model=ArticleResponse)
def update_article(
    req_article: ArticleUpdate,
    article_id: int = Path(gt=0, description="L'ID de l'article doit être un entier positif"),
    db: Session = Depends(get_db),
):
    article = db.get(Article, article_id)
    if article is None:
        raise RessourceNonTrouveException(
            id=article_id, 
            resource_type="article"
        )
    ## fastidieux si on a beaucoup de champs, on peut utiliser un dictionnaire pour faire un update dynamique
    # article.titre = req_article.titre
    # article.contenu = req_article.contenu
    # article.publie = req_article.publie
    
    ## update dynamique
    # rappel: model_dump() retourne un dictionnaire avec les champs et valeurs du modèle Pydantic
    # exclude_none=True permet d'exclure les champs qui sont None, donc on ne met à jour que les champs fournis dans la requête
    for key, value in req_article.model_dump(exclude_none=True).items():
        setattr(article, key, value)
    # UPDATE articles SET titre=..., contenu=..., publie=... WHERE id=...
    db.commit()
    return article