import pickle

from sekg.constant.code import CodeEntityCategory
from sekg.graph.exporter.graph_data import GraphData
from sekg.util.annotation import catch_exception

from definitions import MYSQL_FACTORY
from doc.doc_builder import GraphNodeDocumentBuilder
from util.path_util import PathUtil


@catch_exception
def build_doc_with_type(pro_name, version, api_type):
    graph_data_path = PathUtil.graph_data(pro_name=pro_name, version=version)
    pro_name += "."
    pro_name += memo[api_type]
    document_collection_path = PathUtil.doc(pro_name=pro_name, version=version)
    graph_data_instance = GraphData.load(str(graph_data_path))
    builder = GraphNodeDocumentBuilder(graph_data=graph_data_instance)
    session = MYSQL_FACTORY.create_mysql_session_by_server_name(server_name="89RootServer",
                                                                database="api_backup",
                                                                echo=False)
    builder.build_doc_for_some_type(session, api_type, process=True)
    builder.save(document_collection_path)
    # sub_doc_path = PathUtil.sub_doc(pro_name=pro_name, version=version)
    # builder.extract_kg_doc_collection(sub_doc_path)


if __name__ == '__main__':
    # pro_list = SUPPORT_PROJECT_LIST
    pro_list = ["android27", "jdk8"]
    memo = {CodeEntityCategory.CATEGORY_CLASS: "class", CodeEntityCategory.CATEGORY_METHOD: "method"}
    # versions = ["v1", "v2", "v3"]
    versions = ["v1"]
    type_list = [CodeEntityCategory.CATEGORY_CLASS, CodeEntityCategory.CATEGORY_METHOD]

    for pro_name in pro_list:
        for version in versions:
            for t in type_list:
                build_doc_with_type(pro_name, version, t)
