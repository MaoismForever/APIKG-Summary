from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

metadata = MetaData()


class EngineFactory:
    @staticmethod
    def create_engine_to_api_backup(echo=True):
        engine = create_engine("mysql+pymysql://root:root@10.141.221.73/api_backup?charset=utf8", encoding='utf-8',
                               echo=echo)
        return engine

    @staticmethod
    def create_engine_to_center(echo=True):
        engine = create_engine("mysql+pymysql://root:root@10.141.221.87/domainkg?charset=utf8", encoding='utf-8',
                               echo=echo)
        return engine

    @staticmethod
    def create_engine_by_schema_name(schema_name, echo=True):
        if schema_name == 'stackoverflow':
            engine = create_engine("mysql+pymysql://root:root@10.131.252.160/stackoverflow?charset=utf8",
                                   encoding='utf-8',
                                   echo=echo)
            return engine
        elif schema_name == 'knowledgeGraph':
            engine = create_engine("mysql+pymysql://root:root@10.141.221.75/knowledgeGraph?charset=utf8",
                                   encoding='utf-8',
                                   echo=echo)
            return engine
        elif schema_name == 'api_backup':
            engine = create_engine("mysql+pymysql://root:root@10.141.221.89/api_backup?charset=utf8mb4", encoding='utf-8',
                                   echo=echo)
            return engine
        elif schema_name == 'domainkg':
            engine = create_engine("mysql+pymysql://root:root@10.141.221.89/domainkg?charset=utf8", encoding='utf-8',
                                   echo=echo)
            return engine
        elif schema_name == 'huawei_demo':
            engine = create_engine("mysql+pymysql://root:root@10.141.221.89/huawei_demo?charset=utf8", encoding='utf-8',
                                   echo=echo)
            return engine
        elif schema_name == 'yaml':
            engine = create_engine("mysql+pymysql://root:root@10.141.221.89/yaml?charset=utf8", encoding='utf-8',
                                   echo=echo)
            return engine
        elif schema_name == 'yaml2':
            engine = create_engine("mysql+pymysql://root:root@10.141.221.89/yaml2?charset=utf8", encoding='utf-8',
                                   echo=echo)
            return engine
        elif schema_name == 'ner':
            engine = create_engine("mysql+pymysql://root:root@10.141.221.89/ner?charset=utf8", encoding='utf-8',
                                   echo=echo)
            return engine
        else:
            return None

    @staticmethod
    def create_session(engine=None, autocommit=False, echo=False):
        if engine is None:
            engine = EngineFactory.create_engine_to_center(echo=echo)

        Session = sessionmaker(bind=engine, autocommit=autocommit)
        session = Session()
        return session

    @staticmethod
    def create_session_to_api_backup(autocommit=False, echo=True):

        engine = EngineFactory.create_engine_to_api_backup(echo=echo)

        Session = sessionmaker(bind=engine, autocommit=autocommit)
        session = Session()
        return session

    @staticmethod
    def create_session_to_api_backup_eight_nine(autocommit=False, echo=True):
        engine = EngineFactory.create_engine_by_schema_name('api_backup', echo=echo)

        Session = sessionmaker(bind=engine, autocommit=autocommit)
        session = Session()
        return session