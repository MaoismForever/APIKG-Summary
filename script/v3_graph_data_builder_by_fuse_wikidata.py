#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
sys.path.append('/home/fdse/lvgang/APIKGSummaryV1')

from definitions import SUPPORT_PROJECT_LIST
from graph.builder.graph_builder import CodeGraphBuilder
from util.path_util import PathUtil


def build_v3_graph_for_pro(pro_name):
    builder = CodeGraphBuilder()
    input_graph_data_path = PathUtil.graph_data(pro_name=pro_name, version="v2_1")
    word2vec_model_path = PathUtil.tuned_word2vec(pro_name=pro_name, version="v2")
    pretrain_w2v_path = PathUtil.pretrain_wiki_w2v()
    output_graph_data_path = PathUtil.graph_data(pro_name=pro_name, version="v3")
    concept_list_path = PathUtil.domain_concept_list(pro_name)
    generic_title_search_cache_path = PathUtil.generic_title_search_cache()
    generic_wikidata_item_cache_path = PathUtil.generic_wikidata_item_cache()
    wikidata_fusion_temp_result_dir = PathUtil.wikidata_fusion_temp_result_dir(pro_name)
    project_title_search_cache_path = PathUtil.project_title_search_cache(pro_name)
    project_wikidata_item_cache_path = PathUtil.project_wikidata_item_cache(pro_name)
    graph_data = builder.build_v3_graph_from_cache_with_twice_fuse(pro_name=pro_name,
                                                                   input_graph_data_path=input_graph_data_path,
                                                                   word2vec_model_path=word2vec_model_path,
                                                                   pretrain_w2v_path=pretrain_w2v_path,
                                                                   output_graph_data_path=output_graph_data_path,

                                                                   concept_list=concept_list_path,
                                                                   generic_title_search_cache_path=generic_title_search_cache_path,
                                                                   generic_wikidata_item_cache_path=generic_wikidata_item_cache_path,
                                                                   fusion_temp_result_dir=wikidata_fusion_temp_result_dir,
                                                                   project_title_search_cache_path=project_title_search_cache_path,
                                                                   project_wikidata_item_cache_path=project_wikidata_item_cache_path,

                                                                   )
    # todo: has bug for V3 builder
    graph_data.print_graph_info()


if __name__ == "__main__":

    pro_list = SUPPORT_PROJECT_LIST
    for pro_name in pro_list:
        build_v3_graph_for_pro(pro_name)
