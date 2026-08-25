from sqlalchemy.orm import Session
from database import Article

def get_article_id(
    db: Session,
    article_id: int 
):
    return db.get(Article, article_id)