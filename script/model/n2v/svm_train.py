#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from pathlib import Path

import networkx as nx
from sekg.graph.exporter.graph_data import GraphData

from sekg.graph.exporter.weight_graph_data import WeightGraphData
from sekg.ir.doc.wrapper import PreprocessMultiFieldDocumentCollection, MultiFieldDocumentCollection
from sekg.ir.models.n2v.svm.filter_semantic_tfidf_n2v import FilterSemanticTFIDFNode2VectorModel

from definitions import OUTPUT_DIR, DATA_DIR
from sekg.ir.preprocessor.base import Preprocessor

from util.path_util import PathUtil


class SVMTrainer():
    def __init__(self):
        self.graph_data = GraphData.load(
            str(Path(DATA_DIR / "graph" / ("{pro}.{version}.graph".format(pro="jdk8", version="v4")))))
        model_dir_path = Path(OUTPUT_DIR) / 'svm_model'
        self.model = FilterSemanticTFIDFNode2VectorModel(name="svm", model_dir_path=model_dir_path)
        self.document_collection_path = Path(DATA_DIR) / 'doc' / 'jdk8' / 'jdk8.v4.dc'
        self.collection = MultiFieldDocumentCollection.load(
            str(self.document_collection_path))
        self.processor = Preprocessor()
        self.doc_collection = PreprocessMultiFieldDocumentCollection.create_from_doc_collection(self.processor,
                                                                                                self.collection)
        self.pretrain_node2vec_path = PathUtil.node2vec(pro_name="jdk8", version="v4", weight="unweight")
        self.kg_name_searcher_path = str(Path(
            DATA_DIR / "graph" / ("{pro}.{version}.namesearcher".format(pro="jdk8", version="v4"))))

    def train(self):
        self.model.train_from_doc_collection_with_preprocessor(self.doc_collection,
                                                               pretrain_node2vec_path=self.pretrain_node2vec_path,
                                                               kg_name_searcher_path=self.kg_name_searcher_path)
        self.model.save(str(OUTPUT_DIR / "sim_models" / "jdk8" / "v4" / "svm"))


if __name__ == '__main__':
    svm = SVMTrainer()
    svm.train()
