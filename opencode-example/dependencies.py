from fastapi import Query

# dépendence fonction
def get_query_params(
        q: str = "", 
        page: int = Query(1, gt=0, description="Numéro de la page (doit être un entier positif)"), 
        taille: int = Query(10, gt=0, le=100, description="Nombre d'articles par page (doit être un entier positif entre 1 et 100)")
    ) -> dict:
    return {"q": q, "page": page, "taille": taille}

class GetQueryParams:
    def __init__(
        self,
        q: str = Query("", description="Terme de recherche"),
        page: int = Query(1, gt=0, description="Numéro de la page (doit être un entier positif)"),
        taille: int = Query(10, gt=0, le=100, description="Nombre d'articles par page (doit être un entier positif entre 1 et 100)")
    ):
        self.q = q
        self.page = page
        self.taille = taille