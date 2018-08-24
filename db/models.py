from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Sequence, Text

Base = declarative_base()

class Article(Base):
    __tablename__ = 'article'

    id = Column(Integer, Sequence('article_id_seq'), primary_key=True)
    url = Column(String)
    title = Column(String)
    content = Column(Text)
    raw_content = Column(Text)
    images = Column(Text)
