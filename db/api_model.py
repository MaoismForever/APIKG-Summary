import traceback

from sekg.mysql.sqlalchemy_fulltext import FullText
from sqlalchemy import Column, Integer, ForeignKey, Index, String, Text, func, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class APIRelation(Base):
    ## todo: change to fix the sekg code constant
    RELATION_CATEGORY_BELONG_TO = 1
    RELATION_CATEGORY_EXTENDS = 2
    RELATION_CATEGORY_IMPLEMENTS = 3
    RELATION_CATEGORY_SEE_ALSO = 4
    RELATION_CATEGORY_THROW_EXCEPTION_TYPE = 5
    RELATION_CATEGORY_RETURN_VALUE_TYPE = 6
    RELATION_CATEGORY_HAS_PARAMETER = 7
    RELATION_CATEGORY_HAS_RETURN_VALUE = 8
    RELATION_CATEGORY_HAS_EXCEPTION_CONDITION = 9
    RELATION_CATEGORY_TYPE_OF = 11

    __tablename__ = 'java_api_relation'
    id = Column(Integer, primary_key=True, autoincrement=True)
    start_api_id = Column(Integer, ForeignKey('java_all_api_entity.id', ondelete='CASCADE'), nullable=False, index=True)
    end_api_id = Column(Integer, ForeignKey('java_all_api_entity.id', ondelete='CASCADE'), nullable=False, index=True)
    relation_type = Column(Integer, index=True)

    __table_args__ = (Index('unique_index', start_api_id, end_api_id, relation_type),
                      Index('all_relation_index', start_api_id, end_api_id),
                      {
                          "mysql_charset": "utf8",
                      })

    def __init__(self, start_api_id, end_api_id, relation_type):
        self.start_api_id = start_api_id
        self.end_api_id = end_api_id
        self.relation_type = relation_type

    def exist_in_remote(self, session):
        try:
            if session.query(APIRelation.id).filter_by(start_api_id=self.start_api_id,
                                                       end_api_id=self.end_api_id,
                                                       relation_type=self.relation_type).first():
                return True
            else:
                return False
        except Exception:
            traceback.print_exc()
            return False

    def get_remote_object(self, session):
        if self.id:
            return self
        else:
            try:
                return session.query(APIRelation).filter_by(start_api_id=self.start_api_id,
                                                            end_api_id=self.end_api_id,
                                                            relation_type=self.relation_type).first()
            except Exception:
                # traceback.print_exc()
                return None

    def find_or_create(self, session, autocommit=True):
        remote_instance = self.get_remote_object(session)
        if not remote_instance:
            session.add(self)
            if autocommit:
                session.commit()
            return self
        else:
            return remote_instance

    def __repr__(self):
        return '<APIRelation: %r-%r: type=%r >' % (self.start_api_id, self.end_api_id, self.relation_type)

    @staticmethod
    def get_api_relation_by_start_and_end_api_id(session, start_api_id, end_api_id):
        try:
            api_relation = session.query(APIRelation).filter_by(start_api_id=start_api_id,
                                                                end_api_id=end_api_id).first()
            return api_relation
        except Exception:
            traceback.print_exc()
            return None

    @staticmethod
    def get_type_string(relation_type):
        if relation_type == APIRelation.RELATION_CATEGORY_BELONG_TO:
            return "belong to"
        if relation_type == APIRelation.RELATION_CATEGORY_EXTENDS:
            return "extend"
        if relation_type == APIRelation.RELATION_CATEGORY_IMPLEMENTS:
            return "implement"
        if relation_type == APIRelation.RELATION_CATEGORY_SEE_ALSO:
            return "see also"
        if relation_type == APIRelation.RELATION_CATEGORY_THROW_EXCEPTION_TYPE:
            return "throw exception"
        if relation_type == APIRelation.RELATION_CATEGORY_RETURN_VALUE_TYPE:
            return "return value type"

        if relation_type == APIRelation.RELATION_CATEGORY_HAS_PARAMETER:
            return "has parameter"
        if relation_type == APIRelation.RELATION_CATEGORY_HAS_RETURN_VALUE:
            return "has return value"
        if relation_type == APIRelation.RELATION_CATEGORY_HAS_EXCEPTION_CONDITION:
            return "has exception"

        if relation_type == APIRelation.RELATION_CATEGORY_TYPE_OF:
            return "type of"
        if relation_type == APIRelation.RELATION_CATEGORY_TYPE_OF:
            return "type of"
        if relation_type == APIRelation.RELATION_CATEGORY_TYPE_OF:
            return "type of"
        return ""


class APIEntity(Base, FullText):
    API_TYPE_ALL_API_ENTITY = -1
    API_TYPE_UNKNOWN = 0
    API_TYPE_PACKAGE = 1
    API_TYPE_CLASS = 2 #class
    API_TYPE_INTERFACE = 3 #class
    API_TYPE_EXCEPTION = 4 #class
    API_TYPE_ERROR = 5 #class
    API_TYPE_FIELD = 6 #class
    API_TYPE_CONSTRUCTOR = 7 #method
    API_TYPE_ENUM_CLASS = 8 #class
    API_TYPE_ANNOTATION = 9 #class
    API_TYPE_XML_ATTRIBUTE = 10
    API_TYPE_METHOD = 11 #method
    API_TYPE_ENUM_CONSTANTS = 12
    API_TYPE_PRIMARY_TYPE = 13
    API_TYPE_PARAMETER = 14
    API_TYPE_RETURN_VALUE = 15
    API_TYPE_EXCEPTION_CONDITION = 16
    VALID_API = 1
    INVALID_API = 0

    __tablename__ = 'java_all_api_entity'
    __fulltext_columns__ = ('qualified_name',)
    id = Column(Integer, primary_key=True, autoincrement=True)
    api_type = Column(Integer, default=API_TYPE_UNKNOWN, index=True)
    qualified_name = Column(String(512), index=True)
    full_declaration = Column(String(512), nullable=True, index=True)
    short_description = Column(Text(), nullable=True)
    added_in_version = Column(String(128), nullable=True)
    # document_websites = relationship("APIDocumentWebsite", foreign_keys=[APIDocumentWebsite.api_id], backref="api")

    out_relation = relationship('APIRelation', foreign_keys=[APIRelation.start_api_id], cascade='all, delete-orphan',
                                passive_deletes=True,
                                backref='start_api')
    in_relation = relationship('APIRelation', foreign_keys=[APIRelation.end_api_id], cascade='all, delete-orphan',
                               passive_deletes=True,
                               backref='end_api')

    # all_aliases = relationship(
    #     "APIAlias",
    #     secondary=has_alias_table,
    #     back_populates="all_apis")

    __table_args__ = {
        "mysql_charset": "utf8"
    }

    def __init__(self, qualified_name=None, full_declaration=None, short_description=None,
                 added_in_version=None, api_type=API_TYPE_UNKNOWN):
        self.api_type = api_type
        self.qualified_name = qualified_name
        self.full_declaration = full_declaration
        self.short_description = short_description
        self.added_in_version = added_in_version

    def find_or_create(self, session, autocommit=True):
        if self.api_type == APIEntity.API_TYPE_PARAMETER or self.api_type == APIEntity.API_TYPE_RETURN_VALUE or self.api_type == APIEntity.API_TYPE_EXCEPTION_CONDITION:
            remote_instance = self.get_remote_parameter_object(session)
        else:
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
                return session.query(APIEntity).filter(
                    APIEntity.qualified_name == func.binary(self.qualified_name)).first()
            except Exception:
                traceback.print_exc()
                return None

    def get_remote_parameter_object(self, session):
        if self.id:
            return self
        else:
            try:
                return session.query(APIEntity).filter_by(qualified_name=self.qualified_name,
                                                          full_declaration=self.full_declaration,
                                                          short_description=self.short_description).first()
            except Exception:
                traceback.print_exc()
                return None

    @staticmethod
    def exist(session, qualified_name):
        try:
            if session.query(APIEntity.id).filter(APIEntity.qualified_name == func.binary(qualified_name)).first():
                return True
            else:
                return False
        except Exception:
            traceback.print_exc()
            return None

    @staticmethod
    def delete_by_api_id(session, api_id):
        try:
            session.query(APIEntity).filter_by(id=api_id).delete()
            session.commit()
        except Exception:
            traceback.print_exc()
            return None

    @staticmethod
    def find_by_id(session, api_entity_id):
        try:
            return session.query(APIEntity).filter(APIEntity.id == api_entity_id).first()
        except Exception:
            return None

    @staticmethod
    def find_by_qualifier(session, qualified_name):
        try:
            return session.query(APIEntity).filter(APIEntity.qualified_name == func.binary(qualified_name)).first()
        except Exception:
            traceback.print_exc()
            return None

    @staticmethod
    def find_by_full_declaration_and_description(session, full_declaration, description):
        try:
            return session.query(APIEntity).filter_by(full_declaration=func.binary(full_declaration),
                                                      short_description=description).first()
        except Exception:
            traceback.print_exc()
            return None

    @staticmethod
    def get_api_type_string(type):
        if type == APIEntity.API_TYPE_UNKNOWN:
            return []
        if type == APIEntity.API_TYPE_PACKAGE:
            return ["package"]
        if type == APIEntity.API_TYPE_CLASS:
            return ["class"]
        if type == APIEntity.API_TYPE_INTERFACE:
            return ["interface", "class"]
        if type == APIEntity.API_TYPE_EXCEPTION:
            return ["exception", "class"]
        if type == APIEntity.API_TYPE_ERROR:
            return ["error", "class"]
        if type == APIEntity.API_TYPE_FIELD:
            return ["field", "constant"]
        if type == APIEntity.API_TYPE_CONSTRUCTOR:
            return ["constructor", "constructor method"]
        if type == APIEntity.API_TYPE_ENUM_CLASS:
            return ["enum", "constant", "enum class"]
        if type == APIEntity.API_TYPE_ANNOTATION:
            return ["annotation"]
        if type == APIEntity.API_TYPE_XML_ATTRIBUTE:
            return ["XML attribute", "attribute"]
        if type == APIEntity.API_TYPE_METHOD:
            return ["API", "method"]

        if type == APIEntity.API_TYPE_ENUM_CONSTANTS:
            return ["constant", "enum constant"]
        return []

    @staticmethod
    def get_simple_type_string(type):
        if type == APIEntity.API_TYPE_UNKNOWN:
            return ""
        if type == APIEntity.API_TYPE_PACKAGE:
            return "api package"
        if type == APIEntity.API_TYPE_CLASS:
            return "api class"
        if type == APIEntity.API_TYPE_INTERFACE:
            return "api interface"
        if type == APIEntity.API_TYPE_EXCEPTION:
            return "api exception"
        if type == APIEntity.API_TYPE_ERROR:
            return "api error"
        if type == APIEntity.API_TYPE_FIELD:
            return "api field"
        if type == APIEntity.API_TYPE_CONSTRUCTOR:
            return "api constructor"
        if type == APIEntity.API_TYPE_ENUM_CLASS:
            return "api enum class"
        if type == APIEntity.API_TYPE_ANNOTATION:
            return "api annotation"
        if type == APIEntity.API_TYPE_XML_ATTRIBUTE:
            return "api xml attribute"
        if type == APIEntity.API_TYPE_METHOD:
            return "api method"
        if type == APIEntity.API_TYPE_ENUM_CONSTANTS:
            return "api enum constant"
        if type == APIEntity.API_TYPE_PARAMETER:
            return "api parameter"
        if type == APIEntity.API_TYPE_RETURN_VALUE:
            return "api return value"
        if type == APIEntity.API_TYPE_EXCEPTION_CONDITION:
            return "api exception"
        return ""

    def __repr__(self):
        return '<APIEntity: id=%r name=%r>' % (self.id, self.qualified_name)

    def __eq__(self, other):
        if isinstance(other, APIEntity):
            return self.id == other.id
        else:
            return False

    def __hash__(self):
        return hash(self.id)

    @staticmethod
    def type_string_to_api_type_constant(api_type_string):
        if not api_type_string:
            return APIEntity.API_TYPE_UNKNOWN
        api_type_string = api_type_string.strip()
        if not api_type_string:
            return APIEntity.API_TYPE_UNKNOWN
        api_type_string = api_type_string.lower()
        if api_type_string == "package":
            return APIEntity.API_TYPE_PACKAGE
        if api_type_string == "class":
            return APIEntity.API_TYPE_CLASS
        if api_type_string == "interface":
            return APIEntity.API_TYPE_INTERFACE
        if api_type_string == "error":
            return APIEntity.API_TYPE_ERROR
        if api_type_string == "enum":
            return APIEntity.API_TYPE_ENUM_CLASS
        if api_type_string == "exception":
            return APIEntity.API_TYPE_EXCEPTION
        if api_type_string == "annotation type" or api_type_string == "annotation":
            return APIEntity.API_TYPE_ANNOTATION
        if api_type_string == "method":
            return APIEntity.API_TYPE_METHOD
        if api_type_string == "constructor":
            return APIEntity.API_TYPE_CONSTRUCTOR
        if api_type_string == "nested" or api_type_string == "nested class":
            return APIEntity.API_TYPE_CLASS
        if api_type_string == "required":
            return APIEntity.API_TYPE_FIELD
        if api_type_string == "optional":
            return APIEntity.API_TYPE_FIELD
        if api_type_string == "field":
            return APIEntity.API_TYPE_FIELD
        if api_type_string == "enum constant":
            return APIEntity.API_TYPE_ENUM_CONSTANTS

        return APIEntity.API_TYPE_UNKNOWN

    @staticmethod
    def api_type_belong_to_relation(api_type, subject_api_type):
        if api_type == subject_api_type:
            return True
        if subject_api_type == APIEntity.API_TYPE_METHOD:
            if api_type == APIEntity.API_TYPE_CONSTRUCTOR:
                return True

        if subject_api_type == APIEntity.API_TYPE_CLASS:
            if api_type == APIEntity.API_TYPE_INTERFACE:
                return True
            if api_type == APIEntity.API_TYPE_ERROR:
                return True
            if api_type == APIEntity.API_TYPE_ENUM_CLASS:
                return True
            if api_type == APIEntity.API_TYPE_EXCEPTION:
                return True
        if subject_api_type == APIEntity.API_TYPE_FIELD:

            if api_type == APIEntity.API_TYPE_ENUM_CONSTANTS:
                return True

        return False

    @staticmethod
    def get_api_id_list(session):
        try:
            return session.query(APIEntity.id).all()
        except Exception:
            traceback.print_exc()
            return None

    @staticmethod
    def get_api_id_and_qualified_name_list(session):
        try:
            return session.query(APIEntity.id, APIEntity.qualified_name).all()
        except Exception:
            traceback.print_exc()
            return []

    @staticmethod
    def get_all_API_entity(session):
        try:
            return session.query(APIEntity).all()
        except Exception:
            traceback.print_exc()
            return []

    @staticmethod
    def get_all_value_instance_api(session):
        try:
            return session.query(APIEntity).filter(or_(APIEntity.api_type == APIEntity.API_TYPE_EXCEPTION_CONDITION,
                                                       APIEntity.api_type == APIEntity.API_TYPE_PARAMETER,
                                                       APIEntity.api_type == APIEntity.API_TYPE_RETURN_VALUE)).all()
        except Exception:
            traceback.print_exc()
            return []

class APIHTMLText(Base):
    __tablename__ = 'java_api_html_text'
    id = Column(Integer, primary_key=True, autoincrement=True)
    api_id = Column(Integer, ForeignKey('java_all_api_entity.id'), nullable=False)
    html = Column(LONGTEXT(), nullable=False)
    clean_text = Column(LONGTEXT(), nullable=True)  # text with no html tags
    reserve_part_tag_text = Column(LONGTEXT(), nullable=True)  # text with only code tags text
    html_type = Column(Integer, nullable=True)

    __table_args__ = (Index('api_id_text_type_index', api_id, html_type), {
        "mysql_charset": "utf8",
    })

    HTML_TYPE_UNKNOWN = 0
    HTML_TYPE_API_DECLARATION = 1
    HTML_TYPE_API_SHORT_DESCRIPTION = 2
    HTML_TYPE_API_DETAIL_DESCRIPTION = 3
    HTML_TYPE_METHOD_RETURN_VALUE_DESCRIPTION = 4

    def __init__(self, api_id, html, html_type=HTML_TYPE_UNKNOWN):
        self.api_id = api_id
        self.html = html
        self.html_type = html_type

    def create(self, session, autocommit=True):
        session.add(self)
        if autocommit:
            session.commit()
        return self

    @staticmethod
    def get_by_id(session, id):
        try:
            return session.query(APIHTMLText).filter_by(id=id).first()
        except Exception:
            traceback.print_exc()
            return None

    @staticmethod
    def get_text_by_api_id_and_type(session, api_id, html_type):
        try:
            return session.query(APIHTMLText.clean_text).filter_by(api_id=api_id, html_type=html_type).all()
        except Exception:
            traceback.print_exc()
            return None

    @staticmethod
    def get_api_html_text_by_api_id_and_type(session, api_id, html_type):
        try:
            return session.query(APIHTMLText).filter_by(api_id=api_id, html_type=html_type).first()
        except Exception:
            traceback.print_exc()
            return None

    @staticmethod
    def get_remote_object(session, api_id, html_type):
        try:
            return session.query(APIHTMLText).filter_by(api_id=api_id, html_type=html_type).first()
        except Exception:
            traceback.print_exc()
            return None

    @staticmethod
    def get_html_text_id(session, api_id, html_type):
        try:
            return session.query(APIHTMLText.id).filter_by(api_id=api_id, html_type=html_type).first()
        except Exception:
            traceback.print_exc()
            return None

    def find_or_create(self, session, autocommit=True):
        remote_instance = self.get_remote_object(session, api_id=self.api_id, html_type=self.html_type)
        if not remote_instance:
            session.add(self)
            if autocommit:
                session.commit()
            return self
        else:
            return remote_instance