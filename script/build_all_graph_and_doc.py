from pathlib import Path
from sekg.graph.exporter.graph_data import GraphData
from sekg.ir.doc.wrapper import MultiFieldDocumentCollection, PreprocessMultiFieldDocumentCollection
from sekg.ir.models.avg_w2v import AVGW2VFLModel
from sekg.ir.preprocessor.base import SimplePreprocessor
from sekg.ir.preprocessor.code_text import CodeDocPreprocessor, PureCodePreprocessor
from sekg.ir.preprocessor.spacy import SpacyTextPreprocessor
from sekg.util.annotation import catch_exception
from graph.builder.graph_builder import CodeGraphBuilder
from script.graph_name_searcher.name_searcher import train_name_searcher

from util.path_util import PathUtil
from script.build_graph_data.v1_graph_data_builder import build_v1_jdk
from script.build_graph_data.v2_graph_data_builder_add_sentence import build_v2_graph_for_pro
from script.build_graph_data.v2_1_graph_data_builder_by_fuse_domain import build_v2_1_graph_for_pro
from script.build_graph_data.v3_graph_data_builder_by_fuse_wikidata_simple import build_v3_graph_for_pro


@catch_exception
def build_doc(pro_name, version):
    graph_data_path = PathUtil.graph_data(pro_name=pro_name, version=version)
    document_collection_path = PathUtil.doc(pro_name=pro_name, version=version)

    builder = CodeGraphBuilder()
    builder.build_doc(graph_data_path=graph_data_path, output_doc_collection_path=document_collection_path)


@catch_exception
def build_pre_doc(pro_name, version, preprocessor):
    pre_way = "unknown-pre"
    if isinstance(preprocessor, SimplePreprocessor):
        pre_way = "sim-pre"
    if isinstance(preprocessor, SpacyTextPreprocessor):
        pre_way = "spacy-pre"
    if isinstance(preprocessor, CodeDocPreprocessor):
        pre_way = "code-pre"
    if isinstance(preprocessor, PureCodePreprocessor):
        pre_way = "pure-pre"

    input_doc_collection_path = PathUtil.doc(pro_name=pro_name, version=version)
    output_pre_doc_collection_path = PathUtil.pre_doc(pro_name=pro_name, version=version, pre_way=pre_way)

    builder = CodeGraphBuilder()
    builder.build_pre_doc(input_doc_collection_path, output_pre_doc_collection_path, preprocessor)


def build_extra_model_and_doc(pro_name, version_list):
    for version in version_list:
        preprocessors = [CodeDocPreprocessor()]
        pre_way = "code-pre"
        build_doc(pro_name=pro_name, version=version)
        for preprocessor in preprocessors:
            build_pre_doc(pro_name=pro_name, version=version, preprocessor=preprocessor)

        train_name_searcher(pro_name=pro_name, version=version)

        pre_doc_collection_path = PathUtil.pre_doc(pro_name=pro_name, version=version, pre_way=pre_way)
        preprocess_doc_collection: PreprocessMultiFieldDocumentCollection = PreprocessMultiFieldDocumentCollection.load(
            pre_doc_collection_path)

        word2vec_model_path = PathUtil.sim_model(pro_name=pro_name, version=version, model_type="avg_w2v")
        AVGW2VFLModel.train(model_dir_path=word2vec_model_path,
                            doc_collection=preprocess_doc_collection)


def build_jdk_all_graph_and_doc():
    pro_name = "jdk8"
    build_v1_jdk()
    build_v2_graph_for_pro(pro_name)
    build_v2_1_graph_for_pro(pro_name)
    build_v3_graph_for_pro(pro_name)
    version_list = ["v1", "v2", "v3"]
    # build_extra_model_and_doc(pro_name, version_list)
    for version in version_list:
        build_doc(pro_name, version)
        build_pre_doc(pro_name, version, CodeDocPreprocessor())

if __name__ == "__main__":
    build_jdk_all_graph_and_doc()
