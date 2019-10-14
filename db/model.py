import traceback

import sys
from sekg.mysql.accessor import MySQLAccessor
from sekg.mysql.sqlalchemy_fulltext import FullText
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index, func
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from definitions import MYSQL_FACTORY

Base = declarative_base()


class CodeElementRelation(Base):
    RELATION_TYPE_BELONG_TO = 1
    RELATION_TYPE_EXTENDS = 2
    RELATION_TYPE_IMPLEMENTS = 3
    RELATION_TYPE_SEE_ALSO = 4
    RELATION_TYPE_THROW_EXCEPTION = 5
    # RELATION_TYPE_RETURN_VALUE = 6
    RELATION_TYPE_HAS_PARAMETER = 7
    RELATION_TYPE_HAS_RETURN_VALUE = 8
    # RELATION_TYPE_HAS_EXCEPTION = 9
    RELATION_TYPE_PARAMETER_HAS_TYPE = 10
    RELATION_TYPE_RETURN_VALUE_HAS_TYPE = 11
    RELATION_TYPE_EXCEPTION_HAS_TYPE = 12
    RELATION_TYPE_METHOD_CALL = 13
    RELATION_TYPE_CLASS_OR_INTERFACE_FIELD_HAS_TYPE = 14
    RELATION_TYPE_CLASS_OR_INTERFACE_HAS_FIELD = 15

    __tablename__ = 'code_element_relation'
    id = Column(Integer, primary_key=True, autoincrement=True)
    start_api_id = Column(Integer, ForeignKey('code_element.id', ondelete='CASCADE'), nullable=False, index=True)
    end_api_id = Column(Integer, ForeignKey('code_element.id', ondelete='CASCADE'), nullable=False, index=True)
    relation_type = Column(Integer, index=True)

    __table_args__ = (Index('unique_index', start_api_id, end_api_id, relation_type),
                      Index('all_relation_index', start_api_id, end_api_id),
                      {
                          "mysql_charset": "utf8",
                      })

    def __init__(self, start_api_id=None, end_api_id=None, relation_type=None):
        self.start_api_id = start_api_id
        self.end_api_id = end_api_id
        self.relation_type = relation_type

    def exist_in_remote(self, session):
        try:
            if session.query(CodeElementRelation.id).filter_by(start_api_id=self.start_api_id,
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
                return session.query(CodeElementRelation).filter_by(start_api_id=self.start_api_id,
                                                                    end_api_id=self.end_api_id,
                                                                    relation_type=self.relation_type).first()
            except Exception:
                traceback.print_exc()
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
        return '<CodeElementRelation:id=%r %r-%r: type=%r >' % (
            self.id, self.start_api_id, self.end_api_id, self.relation_type)

    @staticmethod
    def get_api_relation_by_start_and_end_api_id(session, start_api_id, end_api_id):
        try:
            api_relation = session.query(CodeElementRelation).filter_by(start_api_id=start_api_id,
                                                                        end_api_id=end_api_id).first()
            return api_relation
        except Exception:
            traceback.print_exc()
            return None

    @staticmethod
    def delete_all_relation_related_to_api(session, api_id):
        try:
            session.query(CodeElementRelation).filter_by(start_api_id=api_id).delete()
            session.query(CodeElementRelation).filter_by(end_api_id=api_id).delete()
            session.commit()
        except Exception:
            traceback.print_exc()
            return None

    @staticmethod
    def get_type_string(relation_type):
        if relation_type == CodeElementRelation.RELATION_TYPE_BELONG_TO:  # 1
            return "belong to"
        if relation_type == CodeElementRelation.RELATION_TYPE_EXTENDS:  # 2
            return "extend"
        if relation_type == CodeElementRelation.RELATION_TYPE_IMPLEMENTS:  # 3
            return "implement"
        if relation_type == CodeElementRelation.RELATION_TYPE_SEE_ALSO:  # 4
            return "see also"
        if relation_type == CodeElementRelation.RELATION_TYPE_THROW_EXCEPTION:  # 5
            return "throw exception"
        # if relation_type == CodeElementRelation.RELATION_TYPE_RETURN_VALUE:#6
        #     return "return value type"
        if relation_type == CodeElementRelation.RELATION_TYPE_HAS_PARAMETER:  # 7
            return "has parameter"
        if relation_type == CodeElementRelation.RELATION_TYPE_HAS_RETURN_VALUE:  # 8
            return "has return value"
        if relation_type == CodeElementRelation.RELATION_TYPE_PARAMETER_HAS_TYPE:  # 10
            return "has type"
        if relation_type == CodeElementRelation.RELATION_TYPE_RETURN_VALUE_HAS_TYPE:  # 11
            return "has type"
        if relation_type == CodeElementRelation.RELATION_TYPE_EXCEPTION_HAS_TYPE:  # 12
            return "has type"
        if relation_type == CodeElementRelation.RELATION_TYPE_METHOD_CALL:  # 13
            return "method call"
        if relation_type == CodeElementRelation.RELATION_TYPE_CLASS_OR_INTERFACE_FIELD_HAS_TYPE:  # 14
            return "has type"
        if relation_type == CodeElementRelation.RELATION_TYPE_CLASS_OR_INTERFACE_HAS_FIELD:  # 15
            return "has field"
        return ""


class CodeElement(FullText, Base):
    __tablename__ = 'code_element'
    __fulltext_columns__ = ('qualified_name',)
    API_TYPE_UNKNOWN = 0
    API_TYPE_PACKAGE = 1
    API_TYPE_CLASS = 2
    API_TYPE_INTERFACE = 3
    API_TYPE_EXCEPTION = 4
    API_TYPE_ERROR = 5
    API_TYPE_RETURN_VALUE = 6
    API_TYPE_CONSTRUCT = 7
    API_TYPE_ENUM_CLASS = 8
    API_TYPE_ANNOTATION = 9
    API_TYPE_XML_ATTRIBUTE = 10
    API_TYPE_METHOD = 11
    API_TYPE_ENUM_CONSTANTS = 12
    API_TYPE_PRIMARY_TYPE = 13
    API_TYPE_PARAMETER = 14
    API_TYPE_FIELD = 15
    API_TYPE_EXCEPTION_CONDITION = 16
    API_TYPE_METHOD_FIELD = 17
    API_TYPE_ClASS_OR_INTERFACE_FIELD = 18

    id = Column(Integer, primary_key=True, autoincrement=True)
    element_type = Column(Integer, default=API_TYPE_UNKNOWN, index=True)
    qualified_name = Column(String(512), index=True, nullable=False)
    declare = Column(String(1024), nullable=True)
    comment = Column(Text(), nullable=True)
    description = Column(Text(), nullable=True)
    modifier = Column(String(128), nullable=True)
    type_return = Column(String(128), nullable=True)
    added_in_version = Column(String(128), nullable=True)
    java_all_api_id = Column(Integer)

    __table_args__ = {
        "mysql_charset": "utf8"
    }
    out_relation = relationship('CodeElementRelation', foreign_keys=[CodeElementRelation.start_api_id],
                                cascade='all, delete-orphan',
                                passive_deletes=True,
                                backref='start_api')
    in_relation = relationship('CodeElementRelation', foreign_keys=[CodeElementRelation.end_api_id],
                               cascade='all, delete-orphan',
                               passive_deletes=True,
                               backref='end_api')

    def __init__(self, qualified_name=None, declare=None, description=None, comment=None, modifier=None,
                 type_return=None, added_in_version=None, element_type=API_TYPE_UNKNOWN, java_all_api_id=None):
        self.element_type = element_type
        self.qualified_name = qualified_name
        self.declare = declare
        self.description = description
        self.comment = comment
        self.modifier = modifier
        self.type_return = type_return
        self.added_in_version = added_in_version
        self.java_all_api_id = java_all_api_id

    @staticmethod
    def exist(session, qualified_name):
        try:
            if session.query(CodeElement.id).filter(CodeElement.qualified_name == func.binary(qualified_name)).first():
                return True
            else:
                return False
        except Exception:
            traceback.print_exc()
            return None

    @staticmethod
    def get_api_type_string(type):
        if type == CodeElement.API_TYPE_UNKNOWN:  # 0
            return []
        if type == CodeElement.API_TYPE_PACKAGE:  # 1
            return ["package"]
        if type == CodeElement.API_TYPE_CLASS:  # 2
            return ["class"]
        if type == CodeElement.API_TYPE_INTERFACE:  # 3
            return ["interface", "class"]
        if type == CodeElement.API_TYPE_EXCEPTION:  # 4
            return ["exception", "class"]
        if type == CodeElement.API_TYPE_ERROR:  # 5
            return ["error", "class"]
        if type == CodeElement.API_TYPE_RETURN_VALUE:  # 6
            return ["return value"]
        if type == CodeElement.API_TYPE_CONSTRUCT:  # 7
            return ["constructor", "constructor method"]
        if type == CodeElement.API_TYPE_ENUM_CLASS:  # 8
            return ["enum", "constant", "enum class"]
        if type == CodeElement.API_TYPE_ANNOTATION:  # 9
            return ["annotation"]
        if type == CodeElement.API_TYPE_XML_ATTRIBUTE:  # 10
            return ["XML attribute", "attribute"]
        if type == CodeElement.API_TYPE_METHOD:  # 11
            return ["API", "method"]
        if type == CodeElement.API_TYPE_ENUM_CONSTANTS:  # 12
            return ["constant", "enum constant"]
        if type == CodeElement.API_TYPE_PRIMARY_TYPE:  # 13
            return ["class"]
        if type == CodeElement.API_TYPE_PARAMETER:  # 14
            return ["parameter"]
        if type == CodeElement.API_TYPE_FIELD:  # 15
            return ["field", "constant"]
        if type == CodeElement.API_TYPE_METHOD_FIELD:  # 17
            return ["method field"]
        if type == CodeElement.API_TYPE_ClASS_OR_INTERFACE_FIELD:  # 18
            return ["class/interface field"]
        return []

    @staticmethod
    def get_simple_type_string(type):
        if type == CodeElement.API_TYPE_UNKNOWN:  # 0
            return ""
        if type == CodeElement.API_TYPE_PACKAGE:  # 1
            return "project package"
        if type == CodeElement.API_TYPE_CLASS:  # 2
            return "project class"
        if type == CodeElement.API_TYPE_INTERFACE:  # 3
            return "project interface"
        if type == CodeElement.API_TYPE_EXCEPTION:  # 4
            return "project exception"
        # if type == CodeElement.API_TYPE_ERROR:#5
        #     return "project error"
        if type == CodeElement.API_TYPE_RETURN_VALUE:  # 6
            return "project return value"
        if type == CodeElement.API_TYPE_CONSTRUCT:  # 7
            return "project constructor"
        if type == CodeElement.API_TYPE_ENUM_CLASS:  # 8
            return "project enum class"
        if type == CodeElement.API_TYPE_ANNOTATION:  # 9
            return "project annotation"
        if type == CodeElement.API_TYPE_XML_ATTRIBUTE:  # 10
            return "project xml attribute"
        if type == CodeElement.API_TYPE_METHOD:  # 11
            return "project method"
        if type == CodeElement.API_TYPE_ENUM_CONSTANTS:  # 12
            return "project enum constant"
        if type == CodeElement.API_TYPE_PRIMARY_TYPE:  # 13
            return "project class"
        if type == CodeElement.API_TYPE_PARAMETER:  # 14
            return "project parameter"
        if type == CodeElement.API_TYPE_FIELD:  # 15
            return "project field"
        if type == CodeElement.API_TYPE_EXCEPTION_CONDITION:  # 16
            return "project exception"
        if type == CodeElement.API_TYPE_METHOD_FIELD:  # 17
            return "project method field"
        if type == CodeElement.API_TYPE_ClASS_OR_INTERFACE_FIELD:  # 18
            return "project class/interface field"
        return ""

    @staticmethod
    def find_by_id(session, entity_id):
        try:
            return session.query(CodeElement).filter(CodeElement.id == entity_id).first()
        except Exception:
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

    def get_remote_object(self, session):
        if self.id:
            return self
        else:
            try:
                return session.query(CodeElement).filter(
                    CodeElement.qualified_name == func.binary(self.qualified_name),
                    CodeElement.element_type == func.binary(self.element_type),
                    CodeElement.type_return == self.type_return,
                    CodeElement.description == self.description,
                ).first()
            except Exception:
                traceback.print_exc()
                return None


class MethodCode(FullText, Base):
    __tablename__ = 'method_code'
    __fulltext_columns__ = ('code',)

    id = Column(Integer, primary_key=True, autoincrement=True)
    method_id = Column(Integer, nullable=False)
    code = Column(LONGTEXT(), nullable=True)
    __table_args__ = {
        "mysql_charset": "utf8"
    }

    def __init__(self, method_id, code=None):
        self.method_id = method_id
        self.code = code

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
                return session.query(MethodCode).filter_by(method_id=self.method_id).first()
            except Exception:
                # traceback.print_exc()
                return None


if __name__ == "__main__":
    databases = ["jedite",
                 "jabref",
                 "argoUML022",
                 "argoUML024",
                 "argoUML026",
                 "eclipse",
                 "mucommander"]
    MYSQL_FACTORY.create_database_in_server(server_name="87RootServer")

    for database in databases:
        engine = MYSQL_FACTORY.create_mysql_engine_by_server_name(server_name="87RootServer", database=database,
                                                                  echo=True)
        # create the table by using sekg library
        accessor = MySQLAccessor(engine=engine)
        accessor.create_orm_tables(SqlachemyORMBaseClass=Base)
