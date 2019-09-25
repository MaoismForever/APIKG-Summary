import traceback

from sqlalchemy import Column, Integer, String, func
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class WikipediaDocument(Base):
    __tablename__ = 'wiki_pedia'
    id = Column(Integer, primary_key=True, autoincrement=True)
    doc_id = Column(Integer, autoincrement=True)
    url = Column(String(256), index=True, nullable=False)
    title = Column(String(128), index=True, nullable=False)
    content = Column(LONGTEXT())

    __table_args__ = ({
        "mysql_charset": "utf8",
    })

    def __init__(self, doc_id, url, content):
        self.doc_id = doc_id
        self.url = url
        self.content = content

    @staticmethod
    def get_document_by_wikipedia_title(session, title):
        try:
            return session.query(WikipediaDocument).filter_by(title=func.binary(title)).first()
        except Exception:
            traceback.print_exc()
            return None

