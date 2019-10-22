from sekg.graph.accessor import GraphAccessor
from sekg.graph.exporter.graph_data import Neo4jImporter, GraphData
from definitions import GRAPH_FACTORY
from util.path_util import PathUtil

if __name__ == "__main__":
    import_projects = [
        ("jdk8", "87Neo4jApiSummaryJdk")
    ]

    for pro_name, server_name in import_projects:
        graph_client = GRAPH_FACTORY.create_py2neo_graph_by_server_name(server_name=server_name)
        accessor = GraphAccessor(graph_client)
        importer = Neo4jImporter(accessor)

        graph_data_path = PathUtil.graph_data(pro_name=pro_name, version="v3")
        graph_data: GraphData = GraphData.load(graph_data_path)
        print("start import data of {} into neo4j".format(pro_name))
        importer.import_all_graph_data(graph_data)
