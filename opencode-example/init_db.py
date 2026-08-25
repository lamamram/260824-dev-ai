"""
script d'initialisation de la base de données PostgreSQL avec SQLAlchemy
utilise une fonction init_db() idempotente pour créer les tables si elles n'existent pas déjà
"""
from sqlalchemy import select, func
from database import engine, SessionLocal, Base, Utilisateur, Article, Tag, ProfilUtilisateur
import sys

def init_db():
    """
    Initialise la base de données en créant les tables définies dans les modèles SQLAlchemy.
    Cette fonction est idempotente : elle ne recrée pas les tables si elles existent déjà.
    """
    if len(sys.argv) > 1 and sys.argv[1] == "--force-delete":
        # Supprime toutes les tables existantes avant de les recréer
        Base.metadata.drop_all(bind=engine)
        print("Toutes les tables existantes ont été supprimées.")

    # Crée toutes les tables définies dans les modèles SQLAlchemy
    # si elles existent déjà, cette opération est ignorée (idempotente)
    # => CREATE TABLE IF NOT EXISTS ...
    Base.metadata.create_all(bind=engine)
    print("Base de données initialisée avec succès !")
    
    # une session s'ouvre et se ferme !!!
    with SessionLocal() as session:
        print("insertion des utilisateurs...")
        user_admin = Utilisateur(
            username="admin", 
            email="adm@example.com",
            hashed_password="roottoor",
            is_admin=True
        )
        user_admin.hash_password()
        user_normal = Utilisateur(
            username="gars", 
            email="gars@example.com",
            hashed_password="roottoor"
        )
        user_normal.hash_password()
        # add et add_all() génèrent les requêtes INSERT mais ne valident pas encore la transaction
        session.add_all([user_admin, user_normal])
        # print(user_normal)
        
        # flush pour obtenir les IDs générés, les valeurs par défaut et les valeurs calculées par la base de données
        # écrit dans le cache de la session mais ne valide pas encore la transaction
        # ce cache == identity map: permet de retrouver les objets déjà présents dans la session et d'éviter les doublons
        session.flush()
        # print(user_normal)

        print("insertion des articles...")
        article1 = Article(
            titre="Premier article",
            contenu="Contenu du premier article",
            publie=True,
            auteur_id=user_admin.id  # Utilise l'ID généré après flush()
        )
        article2 = Article(
            titre="Deuxième article",
            contenu="Contenu du deuxième article",
            publie=False,
            auteur_id=user_normal.id  # Utilise l'ID généré après flush()
        )
        article3 = Article(
            titre="Troisième article",
            contenu="Contenu du troisième article",
            publie=True,
            auteur_id=user_normal.id  # Utilise l'ID généré après flush()
        )
        session.add_all([article1, article2, article3])
        session.flush()  # Flush pour obtenir les IDs des articles générés par la base de données

        print("insertion des profiles...")
        profil1 = ProfilUtilisateur(
            bio="Je suis l'administrateur du site.",
            utilisateur_id=user_admin.id  # Utilise l'ID généré après flush()
        )
        profil2 = ProfilUtilisateur(
            bio="Je suis un utilisateur normal.",
            utilisateur_id=user_normal.id  # Utilise l'ID généré après flush()
        )
        session.add_all([profil1, profil2])
        session.flush()  # Flush pour obtenir les IDs des profils générés par la base de

        print("insertion des tags...")
        tag1 = Tag(nom="Python")
        tag2 = Tag(nom="SQLAlchemy")
        tag3 = Tag(nom="PostgreSQL")
        session.add_all([tag1, tag2, tag3])
        session.flush()  # Flush pour obtenir les IDs des tags générés par la base de

        print("association des tags aux articles...")
        article1.tags.append(tag1)  # Premier article avec le tag Python
        article1.tags.append(tag2)  # Premier article avec le tag SQLAlchemy
        article2.tags.append(tag3)  # Deuxième article avec le tag PostgreSQL
        article3.tags.append(tag1)  # Troisième article avec le tag Python


        session.commit()  # Valide la transaction et écrit les changements dans la base de données

        print("Vérification des données insérées :")
        # requête SELECT * pour vérifier que l'utilisateur admin a bien été inséré
        stmt = select(Utilisateur).where(Utilisateur.username == "admin")
        
        # execute retourne un Result qui n'est pas directement exploitable
        # scalars retourne un générateur d'objets ScalarResult
        # .all() retourne une liste d'objets Utilisateur et .first() retourne le premier objet Utilisateur ou None si aucun résultat
        # admin = session.execute(stmt).scalars().first()
        
        admin = session.execute(stmt).scalar_one_or_none()
        if admin:
            print(f"Utilisateur admin trouvé : {admin.username}, email : {admin.email}")
        else:
            print("Utilisateur admin non trouvé.")
        
        # requête SELECT COUNT(1) pour vérifier le nombre d'articles insérés
        stmt_count = select(func.count()).select_from(Article)
        article_count = session.execute(stmt_count).scalar_one()
        print(f"Nombre d'articles insérés : {article_count}")

if __name__ == "__main__":
    init_db()