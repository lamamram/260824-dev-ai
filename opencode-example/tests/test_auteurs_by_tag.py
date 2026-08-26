"""Tests de la route GET /auteurs/by_tag (récupération d'un auteur via un tag).

La base `formation` (docker compose) doit être initialisée avec `python init_db.py`.
Les données seedées utilisées ci-dessous :
- tag "PostgreSQL" porté uniquement par l'article 2 (auteur_id=2)
- tag "Python" porté par l'article 1 (auteur_id=1) et l'article 3 (auteur_id=2)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from main import app
from database import SessionLocal, Tag, articles_tags

client = TestClient(app)

TAG_PORTE_PAR_UN_SEUL_ARTICLE = "PostgreSQL"  # seedé, porté par l'article 2 → auteur 2
TAG_PORTE_PAR_PLUSIEURS_AUTEURS = "Python"    # seedé, articles 1 (auteur 1) et 3 (auteur 2)
TAG_SANS_ARTICLE = "pytest-tag-sans-article"  # créé par la fixture, n'est porté par aucun article
TAG_INCONNU = "pytest-tag-que-aucun-article-ne-pourrait-porter"  # n'est même pas créé


@pytest.fixture
def tag_sans_article():
    """Crée un tag qui n'est associé à AUCUN article, propre au test, supprimé à la fin."""
    db = SessionLocal()
    # netoyer d'éventuels résidus de runs précédents pour rester idempotent
    tag_id_existant = db.execute(select(Tag.id).where(Tag.nom == TAG_SANS_ARTICLE)).scalar_one_or_none()
    if tag_id_existant is not None:
        db.execute(articles_tags.delete().where(articles_tags.c.tag_id == tag_id_existant))
        db.execute(select(Tag).where(Tag.nom == TAG_SANS_ARTICLE).delete())
    tag = Tag(nom=TAG_SANS_ARTICLE)
    db.add(tag)
    db.commit()
    db.close()
    yield TAG_SANS_ARTICLE

    db = SessionLocal()
    # on supprime d'abord les éventuelles lignes d'association (contrainte de clé étrangère)
    ids_tags = select(Tag.id).where(Tag.nom == TAG_SANS_ARTICLE)
    db.execute(articles_tags.delete().where(articles_tags.c.tag_id.in_(ids_tags)))
    db.query(Tag).filter(Tag.nom == TAG_SANS_ARTICLE).delete()
    db.commit()
    db.close()


def test_tag_porte_par_un_article_retourne_l_auteur():
    """Un tag existant porté par un article : 200 et le bon auteur est retourné."""
    reponse = client.get("/auteurs/by_tag", params={"tag": TAG_PORTE_PAR_UN_SEUL_ARTICLE})
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["id"] == 2  # article 2 (seed) appartient à l'auteur 2


def test_tag_porte_par_plusieurs_auteurs_retourne_le_premier_par_id():
    """Plusieurs articles portent un même tag avec des auteurs différents :
    l'auteur au plus petit ID est retourné (comportement déterministe documenté)."""
    reponse = client.get("/auteurs/by_tag", params={"tag": TAG_PORTE_PAR_PLUSIEURS_AUTEURS})
    assert reponse.status_code == 200
    assert reponse.json()["id"] == 1  # auteur 1 (article 1) < auteur 2 (article 3)


def test_tag_existant_sans_article_retourne_404():
    """Un tag qui existe dans la table tags mais n'est porté par aucun article : 404 standard."""
    tag_sans_article  # fixture : crée le tag isolé
    reponse = client.get("/auteurs/by_tag", params={"tag": tag_sans_article})
    assert reponse.status_code == 404
    corps = reponse.json()
    assert corps["erreur"] == "AUTEUR_NOT_FOUND"
    assert corps["code"] == 404


def test_tag_inconnu_retourne_404():
    """Un tag qui n'existe pas du tout dans la table tags : 404 avec le corps d'erreur standard."""
    reponse = client.get("/auteurs/by_tag", params={"tag": TAG_INCONNU})
    assert reponse.status_code == 404
    corps = reponse.json()
    assert corps["erreur"] == "AUTEUR_NOT_FOUND"
    assert corps["code"] == 404
