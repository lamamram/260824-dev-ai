## trouver les auteurs par tag

routeur: routers/articles.py
route: GET /articles/tags/{tag}
cruds: cruds/articles.py
schemas: schemas/articles.py

les tags sont des chaînes de caractères, et un article peut avoir plusieurs tags. Le but de cette route est de récupérer tous les auteurs ayant des articles avec un tag spécifique.