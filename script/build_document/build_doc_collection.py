from sekg.graph.exporter.graph_data import GraphData
from sekg.util.annotation import catch_exception
from definitions import MYSQL_FACTORY
from doc.doc_builder import GraphNodeDocumentBuilder
from graph.builder.graph_builder import CodeGraphBuilder
from util.path_util import PathUtil


@catch_exception
def build_doc(pro_name, version):
    graph_data_path = PathUtil.graph_data(pro_name=pro_name, version=version)
    document_collection_path = PathUtil.doc(pro_name=pro_name, version=version)
    builder = CodeGraphBuilder()
    builder.build_doc(graph_data_path=graph_data_path, output_doc_collection_path=document_collection_path)


if __name__ == '__main__':

    pro_list = ["jdk8"]
    versions = ["v4"]

    for pro_name in pro_list:
        for version in versions:
            build_doc(pro_name, version)
