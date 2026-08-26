## suppression des tags à un article

routeur: routers/articles.py
route: DELETE /articles/{article_id}/tags
cruds: cruds/articles.py
schemas: schemas/articles.py

les tags sont des chaînes de caractères, et un article peut avoir plusieurs tags. Le but de cette route est de supprimer un ou plusieurs tags d'un article existant.