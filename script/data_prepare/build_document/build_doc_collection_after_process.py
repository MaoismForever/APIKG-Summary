import pickle

from sekg.constant.code import CodeEntityCategory
from sekg.graph.exporter.graph_data import GraphData
from sekg.util.annotation import catch_exception

from definitions import MYSQL_FACTORY
from doc.doc_builder import GraphNodeDocumentBuilder
from util.path_util import PathUtil


@catch_exception
def build_doc(pro_name, version):
    graph_data_path = PathUtil.graph_data(pro_name=pro_name, version=version)
    document_collection_path = PathUtil.doc(pro_name=pro_name, version=version)
    graph_data_instance = GraphData.load(str(graph_data_path))
    builder = GraphNodeDocumentBuilder(graph_data=graph_data_instance)
    session = MYSQL_FACTORY.create_mysql_session_by_server_name(server_name="89RootServer",
                                                                database="api_backup",
                                                                echo=False)
    builder.build_doc(session, preprocess=True)
    builder.save(document_collection_path)
    # sub_doc_path = PathUtil.sub_doc(pro_name=pro_name, version=version)
    # builder.extract_kg_doc_collection(sub_doc_path)


if __name__ == '__main__':
    # pro_list = SUPPORT_PROJECT_LIST
    pro_list = ["android27", "jdk8",]
    # versions = ["v1", "v2", "v3"]
    versions = ["v1"]

    for pro_name in pro_list:
        for version in versions:
            build_doc(pro_name, version)
