#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import networkx as nx

from sekg.graph.exporter.weight_graph_data import WeightGraphData
from n2v.TriDNR.tridnr import TriDNR


class TriDNRTrainer():
    def __init__(self, graph_data):
        self.graph_data = graph_data
        self.node_num = graph_data.get_node_num()
        self.nx_G_instance = None
        self.agjedges = []
        self.labels_dict = {}
        self.labels = []
        self.docs = []

    def init_graph(self, weight=False):
        if weight is False:
            self.init_unweight_graph()
        else:
            self.init_weight_graph()

    def init_graph_adjedges(self):
        relation_pairs = self.graph_data.get_relation_pairs()
        adjedges_list = {}
        for pairs in relation_pairs:
            if pairs[0] in adjedges_list.keys():
                adjedges_list[pairs[0]].append(pairs[1])
            else:
                adjedges_list[pairs[0]] = [pairs[1]]
        self.agjedges = [([key_node] + adjedges_list[key_node]) for key_node in adjedges_list.keys()]

    def init_graph_lables_and_description(self):
        labels = self.graph_data.get_all_labels()
        labels_dict = {}
        graph_label = []
        description = []
        for index, label in enumerate(labels):
            labels_dict[index] = label
        self.labels_dict = dict(zip(labels_dict.values(), labels_dict.keys()))
        node_ids = self.graph_data.get_node_ids()
        for ids in node_ids:
            node = self.graph_data.find_nodes_by_ids(ids)[0]
            label = list(node["labels"])
            if labels_dict[0] in label:
                label.remove(labels_dict[0])
            if labels_dict[17] in label and len(label) > 1:
                label.remove(labels_dict[17])
            if labels_dict[3] in label and len(label) > 1:
                label.remove(labels_dict[3])
            if labels_dict[2] in label and len(label) > 1:
                label.remove(labels_dict[2])
            if labels_dict[9] in label and len(label) > 1:
                label.remove(labels_dict[9])
            if labels_dict[4] in label and len(label) > 1:
                label.remove(labels_dict[4])
            graph_label.append([str(ids), str(self.labels_dict[label[0]])])
            description.append([str(ids), self.doc_extract(node)])
        self.labels = graph_label
        self.labels_dict = labels_dict
        self.docs = description

    def init_unweight_graph(self):
        node_ids = self.graph_data.get_node_ids()
        relation_pairs = self.graph_data.get_relation_pairs()
        print("node num=%d" % self.node_num)
        print("relation num=%d" % len(relation_pairs))
        G = nx.DiGraph()
        G.add_nodes_from(node_ids)
        G.add_edges_from(relation_pairs, weight=1.0)
        # todo: a relation weight support
        self.nx_G_instance = G
        print("init graph trainer by unweight relations")

    def init_weight_graph(self):

        node_ids = self.graph_data.get_node_ids()
        relation_pairs_with_type = self.graph_data.get_relation_pairs_with_type()
        print("node num=%d" % self.node_num)
        print("relation num=%d" % len(relation_pairs_with_type))

        print(" pre-compute weight start")

        weight_graph_data = WeightGraphData(self.graph_data)
        weight_graph_data.precompute_weight()
        print("pre-compute weight end")

        weight_relation_tuples = []
        for (start_id, relation_type, end_id) in relation_pairs_with_type:
            weight = weight_graph_data.get_relation_tuple_weight(start_node_id=start_id, relation_name=relation_type,
                                                                 end_node_id=end_id)
            weight_relation_tuples.append((start_id, end_id, weight))

        G = nx.DiGraph()
        G.add_nodes_from(node_ids)
        G.add_weighted_edges_from(weight_relation_tuples)
        self.nx_G_instance = G
        print("init graph trainer by weighted relations(tf-idf tuple)")

    def train(self, model_path, numFea=100, train_size=0.2, random_state=2, dm=0, passes=2):
        """
        model the graph vector from rw_path
        :param trainer: the trainer for one graph
        :param model_path: the output word2vec model path
        :param numFea: the dimensions of word2vec
        :param cores: the num of pipeline training
        :return:
        """

        print("save graph2vec training")
        tridnr_model = TriDNR(self.agjedges, self.labels, self.docs, size=numFea, dm=dm, textweight=.8,
                              train_size=train_size, seed=random_state, passes=passes)
        tridnr_model.save(model_path)
        print("save tridnr model to %s" % model_path)
        return tridnr_model

    @staticmethod
    def doc_extract(node):
        doc = ""
        keywords = []
        if "qualified_name" in node["properties"].keys():
            name = node["properties"]["qualified_name"].split(" ")[0]
        elif "term_name" in node["properties"].keys():
            name = node["properties"]["term_name"].split(" ")[0]
        elif "operation_name" in node["properties"].keys():
            name = node["properties"]["operation_name"].split(" ")[0]
        for item in re.findall("[A-Z]*[a-z]*", name):
            if item not in keywords:
                keywords.append(item)
        if "alias" in node["properties"].keys():
            alias = node["properties"]["alias"]
            for alia in alias:
                for item in re.findall("[A-Z]*[a-z]*", alia):
                    if item not in keywords:
                        keywords.append(item)
        if "short_description" in node["properties"].keys():
            if node["properties"]["short_description"] is None:
                node["properties"]["short_description"] = ""
            doc += node["properties"]["short_description"]
        doc += " ".join(keywords)
        return doc
