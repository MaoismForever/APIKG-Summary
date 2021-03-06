#!/usr/bin/env python
# -*- coding: utf-8 -*-
from graph.builder.graph_builder import CodeGraphBuilder
from util.path_util import PathUtil


def build_v3_graph_for_pro(pro_name):
    builder = CodeGraphBuilder()
    input_graph_data_path = PathUtil.graph_data(pro_name=pro_name, version="v3")

    word2vec_model_path = PathUtil.sim_model(pro_name=pro_name, version="v3", model_type="avg_w2v")
    output_graph_data_path = PathUtil.graph_data(pro_name=pro_name, version="v3")
    generic_wikidata_item_cache_path = PathUtil.generic_wikidata_item_cache()
    wikidata_fusion_temp_result_dir = PathUtil.wikidata_fusion_temp_result_dir(pro_name)

    graph_data = builder.build_v3_graph_from_cache_simple(pro_name=pro_name,
                                                          input_graph_data_path=input_graph_data_path,
                                                          word2vec_model_path=word2vec_model_path,
                                                          output_graph_data_path=output_graph_data_path,
                                                          generic_title_search_cache_path=None,
                                                          generic_wikidata_item_cache_path=generic_wikidata_item_cache_path,
                                                          fusion_temp_result_dir=wikidata_fusion_temp_result_dir,
                                                          )
    graph_data.print_graph_info()


if __name__ == "__main__":
    build_v3_graph_for_pro("jdk8")
