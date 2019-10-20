from pathlib import Path

from sekg.graph.exporter.graph_data import GraphData
from sekg.model.node2vec.train import GraphNode2VecTrainer

from definitions import OUTPUT_DIR, SUPPORT_PROJECT_LIST
from util.annotation import catch_exception


@catch_exception
def train_node2vec(pro_name, version):
    print("train node2vec for %s at version %s" % (pro_name, version))
    graph_data_output_dir = Path(OUTPUT_DIR) / "graph" / pro_name
    graph_data_output_dir.mkdir(exist_ok=True, parents=True)
    node2vec_output_dir = graph_data_output_dir / "GraphEmbedding"
    node2vec_output_dir.mkdir(exist_ok=True, parents=True)
    # train_weight_graph_data(graph_data_output_dir, node2vec_output_dir, pro_name, version)
    graph_random_walk_path = str(
        node2vec_output_dir / "{pro}.{version}.unweight.rwp".format(pro=pro_name, version=version))
    trainer = GraphNode2VecTrainer(GraphData.load(
        str(graph_data_output_dir / ("{pro}.{version}.graph".format(pro=pro_name, version=version)))))
    trainer.init_unweight_graph()
    trainer.generate_random_path(rw_path_store_path=graph_random_walk_path)
    graph2vec_model_path = str(
        node2vec_output_dir / "{pro}.{version}.unweight.node2vec".format(pro=pro_name, version=version))
    GraphNode2VecTrainer.train(rw_path_store_path=graph_random_walk_path, model_path=graph2vec_model_path,
                               dimensions=100)


def train_weight_graph_data(graph_data_output_dir, node2vec_output_dir, pro_name, version):
    graph_random_walk_path = str(
        node2vec_output_dir / "{pro}.{version}.weight.rwp".format(pro=pro_name, version=version))
    trainer = GraphNode2VecTrainer(
        GraphData.load(str(graph_data_output_dir / ("{pro}.{version}.graph".format(pro=pro_name, version=version)))))
    trainer.init_weight_graph(weight=True)
    trainer.generate_random_path(rw_path_store_path=graph_random_walk_path)
    graph2vec_model_path = str(
        node2vec_output_dir / "{pro}.{version}.weight.node2vec".format(pro=pro_name, version=version))
    GraphNode2VecTrainer.train(rw_path_store_path=graph_random_walk_path, model_path=graph2vec_model_path,
                               dimensions=100)


if __name__ == "__main__":

    pro_list = SUPPORT_PROJECT_LIST
    versions = ["v3_1"]
    for version in versions:
        for pro_name in pro_list:
            train_node2vec(pro_name, version)
