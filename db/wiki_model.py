import traceback

from sqlalchemy import Column, Integer, String, func, Float
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


class WikidataAnnotation(Base):
    __tablename__ = 'wikidata_annotation'
    id = Column(Integer, primary_key=True, autoincrement=True)
    wd_item_id = Column(String(32), nullable=True, index=True)
    type = Column(Integer, index=True)
    url = Column(String(256), index=True, nullable=True)
    name = Column(String(256), index=True, nullable=True)
    description = Column(String(1024), index=True, nullable=True)

    __table_args__ = ({
        "mysql_charset": "utf8",
    })

    def __init__(self, wd_item_id, type, description, url, name):
        self.wd_item_id = wd_item_id
        self.type = type
        self.description = description
        self.url = url
        self.name = name

    def find_or_create(self, session, autocommit=True):
        remote_instance = self.get_remote_object(session)
        if not remote_instance:
            session.add(self)
            if autocommit:
                session.commit()
            return self
        else:
            return remote_instance

    def get_remote_object(self, session):
        if self.id:
            return self
        else:
            try:
                result = session.query(WikidataAnnotation).filter(
                    WikidataAnnotation.wd_item_id == self.wd_item_id).first()
                return result
            except Exception:
                traceback.print_exc()
                return None


class WikidataAnnotation1(Base):
    __tablename__ = 'wikidata_annotation_for_annotation1'
    id = Column(Integer, primary_key=True, autoincrement=True)
    wd_item_id = Column(String(32), nullable=True, index=True)
    type = Column(Integer, index=True)
    url = Column(String(256), index=True, nullable=True)
    name = Column(String(256), index=True, nullable=True)
    description = Column(String(1024), index=True, nullable=True)

    __table_args__ = ({
        "mysql_charset": "utf8",
    })

    def __init__(self, wd_item_id, type, description, url, name):
        self.wd_item_id = wd_item_id
        self.type = type
        self.description = description
        self.url = url
        self.name = name

    def find_or_create(self, session, autocommit=True):
        remote_instance = self.get_remote_object(session)
        if not remote_instance:
            session.add(self)
            if autocommit:
                session.commit()
            return self
        else:
            return remote_instance

    def get_remote_object(self, session):
        if self.id:
            return self
        else:
            try:
                result = session.query(WikidataAnnotation).filter(
                    WikidataAnnotation.wd_item_id == self.wd_item_id).first()
                return result
            except Exception:
                traceback.print_exc()
                return None


class WikidataAnnotation2(Base):
    __tablename__ = 'wikidata_annotation_for_annotation2'
    id = Column(Integer, primary_key=True, autoincrement=True)
    wd_item_id = Column(String(32), nullable=True, index=True)
    type = Column(Integer, index=True)
    url = Column(String(256), index=True, nullable=True)
    name = Column(String(256), index=True, nullable=True)
    description = Column(String(1024), index=True, nullable=True)

    __table_args__ = ({
        "mysql_charset": "utf8",
    })

    def __init__(self, wd_item_id, type, description, url, name):
        self.wd_item_id = wd_item_id
        self.type = type
        self.description = description
        self.url = url
        self.name = name

    def find_or_create(self, session, autocommit=True):
        remote_instance = self.get_remote_object(session)
        if not remote_instance:
            session.add(self)
            if autocommit:
                session.commit()
            return self
        else:
            return remote_instance

    def get_remote_object(self, session):
        if self.id:
            return self
        else:
            try:
                result = session.query(WikidataAnnotation).filter(
                    WikidataAnnotation.wd_item_id == self.wd_item_id).first()
                return result
            except Exception:
                traceback.print_exc()
                return None


class ClassifiedWikipediaDocumentLR(Base):
    TYPE_SOFTWARE_RELATED = 1
    TYPE_SOFTWARE_UNRELATED = 0

    __tablename__ = 'classified_wiki_doc_lr_v2'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(128), index=True, nullable=True)
    url = Column(String(256), index=True, nullable=False)
    content = Column(LONGTEXT(), nullable=True)
    type = Column(Integer, index=True, nullable=False)
    score = Column(Float, index=True, nullable=False)
    # wikipedia_doc_id = Column(Integer, ForeignKey('wiki_pedia.id'), nullable=False)
    wikipedia_doc_id = Column(Integer, nullable=False, index=True)

    __table_args__ = ({
        "mysql_charset": "utf8",
    })

    def __init__(self, title, url, type, score, wikipedia_doc_id):
        self.title = title
        self.url = url
        self.type = type
        self.score = score
        self.wikipedia_doc_id = wikipedia_doc_id

    def find_or_create(self, session, autocommit=True):
        remote_instance = self.get_remote_object(session)
        if not remote_instance:
            session.add(self)
            if autocommit:
                session.commit()
            return self
        else:
            return remote_instance

    def create(self, session):
        session.add(self)

    def get_remote_object(self, session):
        if self.id:
            return self
        else:
            try:
                return session.query(ClassifiedWikipediaDocumentLR).filter(
                    ClassifiedWikipediaDocumentLR.wikipedia_doc_id == self.wikipedia_doc_id).first()
            except Exception:
                traceback.print_exc()
                return None

    @staticmethod
    def get_classified_doc(session, wikipedia_doc_id):
        try:
            instance = session.query(ClassifiedWikipediaDocumentLR).filter(
                ClassifiedWikipediaDocumentLR.wikipedia_doc_id == wikipedia_doc_id).first()
            return instance
        except Exception:
            traceback.print_exc()
            return None

    def __repr__(self):
        return '<ClassifiedWikipediaDocumentLR: title=%r score=%r>' % (self.title, self.score)

    @staticmethod
    def delete_all(session):
        try:
            session.query(ClassifiedWikipediaDocumentLR).delete()
            session.commit()
        except Exception:
            traceback.print_exc()
            return


class WikidataAndWikipediaData(Base):
    __tablename__ = 'wikidata_wikipedia_data'
    id = Column(Integer, primary_key=True, autoincrement=True)
    wd_item_id = Column(String(32), nullable=True, index=True)
    wd_item_name = Column(String(256), nullable=True, index=True)
    wikipedia_url = Column(String(256), nullable=True, index=True)
    wikipedia_title = Column(String(128), nullable=True, index=True)
    wikipedia_text = Column(LONGTEXT(), nullable=True)
    data_json = Column(LONGTEXT(), nullable=True)

    __table_args__ = ({
        "mysql_charset": "utf8",
    })

    def __init__(self, wd_item_id, wd_item_name, wikipedia_url, wikipedia_title, wikipedia_text, data_json):
        self.wd_item_id = wd_item_id
        self.wd_item_name = wd_item_name
        self.data_json = data_json
        self.wikipedia_url = wikipedia_url
        self.wikipedia_title = wikipedia_title
        self.wikipedia_text = wikipedia_text

    def find_or_create(self, session, autocommit=True):
        remote_instance = self.get_remote_object(session)
        if not remote_instance:
            session.add(self)
            if autocommit:
                session.commit()
            return self
        else:
            return remote_instance

    @staticmethod
    def is_exist_wikidata_json(session, wd_item_id):

        try:
            if wd_item_id:
                result = session.query(WikidataAndWikipediaData).filter(
                    WikidataAndWikipediaData.wd_item_id == wd_item_id).first()
                if result:
                    return True
            return False
        except Exception:
            traceback.print_exc()
            return False

    @staticmethod
    def is_exist_wikipedia_url(session, wikipeida_url):

        try:
            if wikipeida_url:
                result = session.query(WikidataAndWikipediaData).filter(
                    WikidataAndWikipediaData.wikipedia_url == wikipeida_url).first()
                if result:
                    return True
            return False
        except Exception:
            traceback.print_exc()
            return False

    def get_remote_object(self, session):
        if self.id:
            return self
        else:
            try:
                if self.wd_item_id:
                    result = session.query(WikidataAndWikipediaData).filter(
                        WikidataAndWikipediaData.wd_item_id == self.wd_item_id).first()
                    if result:
                        return result
                if self.wikipedia_url:
                    result = session.query(WikidataAndWikipediaData).filter(
                        WikidataAndWikipediaData.wikipedia_url == self.wikipedia_url).first()

                    return result
            except Exception:
                traceback.print_exc()
                return None
