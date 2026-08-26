"""Tests de la route POST /articles/{article_id}/tags (ajout de tags à un article).

La base `formation` (docker compose) doit être initialisée avec `python init_db.py`.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from main import app
from database import SessionLocal, Article, Tag, articles_tags

client = TestClient(app)

TAG_NOUVEAU = "pytest-tag-nouveau"
TAGS_NOUVEAUX = ["pytest-tag-nouveau", "pytest-tag-bis"]
TAG_EXISTANT = "Python"  # seedé par init_db.py


@pytest.fixture
def article_de_test():
    """Crée un article sans tags propre au test, supprimé à la fin."""
    db = SessionLocal()
    article = Article(
        titre="Article de test tags",
        contenu="Contenu de test pour les tags (10+ car)",
        publie=False,
        auteur_id=1,
    )
    db.add(article)
    db.commit()
    article_id = article.id
    db.close()
    yield article_id

    db = SessionLocal()
    # supprimer d'abord TOUTES les lignes d'association qui référencent les
    # tags de test (y compris des articles résiduels de runs précédents),
    # sinon la suppression des tags viole la contrainte de clé étrangère
    ids_tags = select(Tag.id).where(Tag.nom.in_(TAGS_NOUVEAUX))
    db.execute(articles_tags.delete().where(articles_tags.c.tag_id.in_(ids_tags)))
    # supprimer l'article de test et le(s) tag(s) créé(s) pendant le test
    article_obj = db.get(Article, article_id)
    if article_obj is not None:
        db.delete(article_obj)
    db.query(Tag).filter(Tag.nom.in_(TAGS_NOUVEAUX)).delete()
    db.commit()
    db.close()


def test_post_article_inexistant_retourne_404():
    """Un POST sur un article inconnu retourne 404 avec le corps d'erreur standard."""
    reponse = client.post("/articles/99999999/tags", json={"tags": [TAG_NOUVEAU]})
    assert reponse.status_code == 404
    assert reponse.json()["erreur"] == "ARTICLE_NOT_FOUND"


def test_ajouter_un_nouveau_tag(article_de_test):
    """POST un tag inconnu : il est créé dans la table tags et associé à l'article."""
    reponse = client.post(f"/articles/{article_de_test}/tags", json={"tags": [TAG_NOUVEAU]})
    assert reponse.status_code == 200
    corps = reponse.json()
    # les tags existants et le nouveau tag sont tous renvoyés dans la réponse
    noms_tags = [tag["nom"] for tag in corps["tags"]]
    assert TAG_NOUVEAU in noms_tags

    # vérification dans la base : le nouveau tag est bien associé à l'article
    db = SessionLocal()
    rechargement = db.get(Article, article_de_test)
    db.close()
    assert TAG_NOUVEAU in [tag.nom for tag in rechargement.tags]


def test_ajouter_plusieurs_nouveaux_tags(article_de_test):
    """POST plusieurs tags inconnus : tous sont créés et associés en une seule requête."""
    reponse = client.post(f"/articles/{article_de_test}/tags", json={"tags": TAGS_NOUVEAUX})
    assert reponse.status_code == 200
    corps = reponse.json()
    noms_tags = [tag["nom"] for tag in corps["tags"]]
    assert set(TAGS_NOUVEAUX) <= set(noms_tags)

    db = SessionLocal()
    rechargement = db.get(Article, article_de_test)
    db.close()
    assert set(TAGS_NOUVEAUX) <= {tag.nom for tag in rechargement.tags}

def test_ajouter_un_tag_deja_existant(article_de_test):
    """POST un tag déjà présent dans la table tags : il n'est pas dupliqué, mais associé à l'article."""
    reponse = client.post(f"/articles/{article_de_test}/tags", json={"tags": [TAG_EXISTANT]})
    assert reponse.status_code == 200
    corps = reponse.json()
    assert sum(1 for tag in corps["tags"] if tag["nom"] == TAG_EXISTANT) == 1

    # vérification dans la base : un seul tag "Python" existe, et il est associé à l'article
    db = SessionLocal()
    nb_tags = db.query(Tag).filter(Tag.nom == TAG_EXISTANT).count()
    rechargement = db.get(Article, article_de_test)
    db.close()
    assert nb_tags == 1
    assert sum(1 for tag in rechargement.tags if tag.nom == TAG_EXISTANT) == 1
