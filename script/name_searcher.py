from sekg.graph.util.name_searcher import KGNameSearcher
from sekg.util.annotation import catch_exception
from doc.node_info import ProjectKGNodeInfoFactory
from util.path_util import PathUtil


@catch_exception
def train_name_searcher(pro_name, version):
    print("train graph name searcher for %s at version %s" % (pro_name, version))
    name_searcher_path = PathUtil.name_searcher(pro_name=pro_name, version=version)

    graph_data_path = PathUtil.graph_data(pro_name=pro_name, version=version)

    searcher = KGNameSearcher.train_from_graph_data_file(graph_data_path=graph_data_path,
                                                         node_info_factory=ProjectKGNodeInfoFactory())
    searcher.save(name_searcher_path)
    print("finish... save to %s" % name_searcher_path)


if __name__ == "__main__":
    train_name_searcher(pro_name="jdk8", version="v3")
