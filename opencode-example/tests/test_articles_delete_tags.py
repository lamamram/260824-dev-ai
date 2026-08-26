"""Tests de la route DELETE /articles/{article_id}/tags (suppression de tags d'un article).

La base `formation` (docker compose) doit être initialisée avec `python init_db.py`.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from main import app
from database import SessionLocal, Article, Tag, articles_tags

client = TestClient(app)

TAG_DE_TEST = "pytest-tag-suppression"
TAG_AUSSI = "pytest-tag-suppression-bis"
TAG_EXISTANT = "Python"  # seedé par init_db.py
TAG_INEXISTANT = "PostgreSQL"  # seedé par init_db.py, porté par un autre article


@pytest.fixture
def article_de_test():
    """Crée un article portant deux tags, propre au test, supprimé à la fin."""
    db = SessionLocal()
    article = Article(
        titre="Article de test suppression tags",
        contenu="Contenu de test pour la suppression de tags",
        publie=False,
        auteur_id=1,
    )
    db.add(article)
    db.flush()
    tag1 = db.execute(select(Tag).where(Tag.nom == TAG_EXISTANT)).scalar_one_or_none()
    if tag1 is None:
        tag1 = Tag(nom=TAG_EXISTANT)
        db.add(tag1)
        db.flush()  # générer l'ID pour l'association
    tag2 = db.execute(select(Tag).where(Tag.nom == TAG_DE_TEST)).scalar_one_or_none()
    if tag2 is None:
        tag2 = Tag(nom=TAG_DE_TEST)
        db.add(tag2)
        db.flush()
    article.tags.append(tag1)
    article.tags.append(tag2)
    db.commit()
    article_id = article.id
    db.close()
    yield article_id

    db = SessionLocal()
    # supprimer d'abord TOUTES les lignes d'association qui référencent les
    # tags de test, sinon la suppression des tags viole la contrainte de clé étrangère
    ids_tags = select(Tag.id).where(Tag.nom.in_([TAG_DE_TEST, TAG_AUSSI]))
    db.execute(articles_tags.delete().where(articles_tags.c.tag_id.in_(ids_tags)))
    article_obj = db.get(Article, article_id)
    if article_obj is not None:
        db.delete(article_obj)
    db.query(Tag).filter(Tag.nom.in_([TAG_DE_TEST, TAG_AUSSI])).delete()
    db.commit()
    db.close()


def test_delete_article_inexistant_retourne_404():
    """Un DELETE sur un article inconnu retourne 404 avec le corps d'erreur standard."""
    reponse = client.request("DELETE", "/articles/99999999/tags", json={"tags": [TAG_EXISTANT]})
    assert reponse.status_code == 404
    assert reponse.json()["erreur"] == "ARTICLE_NOT_FOUND"


def test_supprimer_un_tag(article_de_test):
    """DELETE un tag porté par l'article : l'association est retirée, l'autre tag reste."""
    reponse = client.request("DELETE", f"/articles/{article_de_test}/tags", json={"tags": [TAG_EXISTANT]})
    assert reponse.status_code == 200
    corps = reponse.json()
    noms_tags = [tag["nom"] for tag in corps["tags"]]
    assert TAG_EXISTANT not in noms_tags
    assert TAG_DE_TEST in noms_tags

    # vérification dans la base : plus d'association article-tag pour ce tag
    db = SessionLocal()
    rechargement = db.get(Article, article_de_test)
    db.close()
    noms_bases = [tag.nom for tag in rechargement.tags]
    assert TAG_EXISTANT not in noms_bases
    assert TAG_DE_TEST in noms_bases


def test_supprimer_plusieurs_tags(article_de_test):
    """DELETE plusieurs tags d'un article : toutes les associations sont retirées."""
    db = SessionLocal()
    tag_bis = db.execute(select(Tag).where(Tag.nom == TAG_AUSSI)).scalar_one_or_none()
    if tag_bis is None:
        tag_bis = Tag(nom=TAG_AUSSI)
        db.add(tag_bis)
        db.flush()
    article = db.get(Article, article_de_test)
    article.tags.append(tag_bis)
    db.commit()
    article_id = article_de_test
    db.close()

    reponse = client.request(
        "DELETE",
        f"/articles/{article_id}/tags",
        json={"tags": [TAG_EXISTANT, TAG_DE_TEST, TAG_AUSSI]},
    )
    assert reponse.status_code == 200
    assert reponse.json()["tags"] == []

    db = SessionLocal()
    rechargement = db.get(Article, article_id)
    db.close()
    assert [tag.nom for tag in rechargement.tags] == []


def test_supprimer_un_tag_non_porte_par_l_article(article_de_test):
    """DELETE un tag que l'article ne porte pas : 200, les tags de l'article sont inchangés."""
    reponse = client.request("DELETE", f"/articles/{article_de_test}/tags", json={"tags": [TAG_INEXISTANT]})
    assert reponse.status_code == 200
    corps = reponse.json()
    noms_tags = {tag["nom"] for tag in corps["tags"]}
    assert noms_tags == {TAG_EXISTANT, TAG_DE_TEST}

    db = SessionLocal()
    rechargement = db.get(Article, article_de_test)
    db.close()
    assert {tag.nom for tag in rechargement.tags} == {TAG_EXISTANT, TAG_DE_TEST}
