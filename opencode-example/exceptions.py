class RessourceNonTrouveException(Exception):
    def __init__(self, id: int, resource_type: str):
        self.id = id
        self.resource_type = resource_type