#!/usr/bin/env python
# -*- coding: utf-8 -*-
from graph.builder.graph_builder import CodeGraphBuilder
from util.path_util import PathUtil


def build_v2_graph_for_pro(pro_name):
    builder = CodeGraphBuilder()
    input_graph_data_path = PathUtil.graph_data(pro_name=pro_name, version="v2")
    print(input_graph_data_path)
    output_graph_data_path = PathUtil.graph_data(pro_name=pro_name, version="v2_1")
    domain_concept_output_dir = PathUtil.domain_concept_dir(pro_name=pro_name, version="v2")
    builder.build_v2_graph(pro_name=pro_name,
                           input_graph_data_path=input_graph_data_path,
                           output_graph_data_path=output_graph_data_path,
                           domain_concept_output_dir=domain_concept_output_dir
                           )


if __name__ == "__main__":
    pro_list = ['jdk8']
    for pro_name in pro_list:
        build_v2_graph_for_pro(pro_name)
