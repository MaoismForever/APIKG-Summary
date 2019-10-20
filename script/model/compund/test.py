from sekg.graph.exporter.graph_data import GraphData
from sekg.ir.models.bm25 import BM25Model
from sekg.ir.models.compound import CompoundSearchModel
from sekg.ir.models.n2v.svm.avg_n2v import AVGNode2VectorModel
from sekg.ir.models.n2v.svm.filter_semantic_tfidf_n2v import FilterSemanticTFIDFNode2VectorModel

from definitions import OUTPUT_DIR
from pathlib import Path

from util.path_util import PathUtil

if __name__ == '__main__':
    pro_name = "jdk8"
    version = "v3_1"
    compound_model_name = "compound_{base_model}+{extra_model}".format(base_model="bm25", extra_model="avg_n2v")
    model_dir_path = PathUtil.sim_model(pro_name=pro_name, version=version, model_type=compound_model_name)
    model = CompoundSearchModel.load(model_dir_path)
    graph_data_path = PathUtil.graph_data(pro_name=pro_name, version=version)
    graph_data: GraphData = GraphData.load(graph_data_path)
    valid_class_ids = graph_data.get_node_ids_by_label("class")
    valid_method_ids = graph_data.get_node_ids_by_label("method")
    valid_method_ids.update(graph_data.get_node_ids_by_label("base override method"))
    valid_sentence_ids = graph_data.get_node_ids_by_label("sentence")
    while True:
        query = input("please input query: ")
        select = int(input("1、class; 2、methos; 3、sentence"))
        top_num = int(input("please input top num"))
        result = []
        if select == 1:
            result = model.search(query=query, top_num=top_num, valid_doc_id_set=valid_class_ids)
        elif select == 2:
            result = model.search(query=query, top_num=top_num, valid_doc_id_set=valid_method_ids)
        elif select == 3:
            result = model.search(query=query, top_num=top_num, valid_doc_id_set=valid_sentence_ids)
        else:
            print("invalid input")
        for index, item in enumerate(result):
            print(index, " ", item)
