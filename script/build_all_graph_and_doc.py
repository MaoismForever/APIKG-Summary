from pathlib import Path

from sekg.graph.exporter.graph_data import GraphData
from sekg.ir.doc.wrapper import MultiFieldDocumentCollection
from sekg.ir.preprocessor.base import SimplePreprocessor
from sekg.ir.preprocessor.code_text import CodeDocPreprocessor, PureCodePreprocessor
from sekg.ir.preprocessor.spacy import SpacyTextPreprocessor
from sekg.util.annotation import catch_exception

from definitions import SUPPORT_PROJECT_LIST
from graph.builder.graph_builder import CodeGraphBuilder
from script.build_graph_data.jdk.jdk_graph_data_builder import build_v1_android
from script.build_graph_data.jdk.jdk_graph_data_builder import build_v1_jdk
from script.build_graph_data.model.build_all_version_model import train_bm25_method_search_model, \
    train_bm25_graph_sim_model
from script.build_graph_data.v1_graph_data_builder import build_v1_graph_for_pro
from script.build_graph_data.v2_graph_data_builder_by_fuse_domain import build_v2_graph_for_pro
from script.build_graph_data.v3_graph_data_builder_by_fuse_wikidata import build_v3_graph_for_pro
from script.build_graph_data.v4_2_1_graph_data_builder_add_reverse_edges import build_small_graph_4_2_1_for_pro
from script.build_graph_data.v4_graph_data_builder_by_fuse_jdk import build_v4_graph_for_pro
from script.build_graph_data.v4_plus_graph_data_builder_by_reduce_graph_size import build_small_v4_plus_graph_for_pro
from script.graph2vec.train_unweight_n2v import train_unweight_node2vec
from script.name_searcher.train_name_searcher import train_name_searcher
from script.word2vec.train_tune_word2vec_based_on_project import train_tune_word_embedding
from util.node_id_util import NodeIDUtil
from util.path_util import PathUtil


@catch_exception
def build_method_code_doc(pro_name):
    graph_data_path = PathUtil.graph_data(pro_name=pro_name, version="v1")
    code_doc_collection_path = PathUtil.code_doc_collection(pro_name)
    method_code_doc_collection_path = PathUtil.method_code_doc_collection(pro_name)
    graph_data: GraphData = GraphData.load(graph_data_path)
    method_ids = NodeIDUtil.valid_project_method_ids_from_graph_data(graph_data=graph_data, pro_name=pro_name)

    code_doc_collection: MultiFieldDocumentCollection = MultiFieldDocumentCollection.load(code_doc_collection_path)

    method_code_doc_collection = code_doc_collection.sub_document_collection(method_ids)
    method_code_doc_collection.save(method_code_doc_collection_path)
    return method_code_doc_collection


@catch_exception
def build_pre_method_code_doc(pro_name):
    builder = CodeGraphBuilder()

    method_code_doc_collection_path = PathUtil.method_code_doc_collection(pro_name)
    pre_method_code_doc_collection = PathUtil.pre_method_code_doc_collection(pro_name)

    builder.build_pre_doc(input_doc_collection_path=method_code_doc_collection_path,
                          output_pre_doc_collection_path=pre_method_code_doc_collection,
                          preprocessor=PureCodePreprocessor())


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

        build_doc(pro_name=pro_name, version=version)
        for preprocessor in preprocessors:
            build_pre_doc(pro_name=pro_name, version=version, preprocessor=preprocessor)
        train_name_searcher(pro_name=pro_name, version=version)
        train_unweight_node2vec(pro_name=pro_name, version=version)
        train_tune_word_embedding(pro_name, version, pre_way="code-pre")


def build_jdk_all_graph_and_doc():
    pro_name = "jdk8"
    build_v1_jdk()
    build_v2_graph_for_pro(pro_name)
    build_v3_graph_for_pro(pro_name)

    version_list = ["v1", "v2", "v3"]
    build_extra_model_and_doc(pro_name, version_list)

def build_project_all_graph_and_doc(pro_name):
    build_v1_graph_for_pro(pro_name)
    build_v2_graph_for_pro(pro_name)
    build_v3_graph_for_pro(pro_name)
    build_v4_graph_for_pro(pro_name)
    build_small_v4_plus_graph_for_pro(pro_name)
    build_small_graph_4_2_1_for_pro(pro_name)
    version_list = ["v1", "v2", "v3", "v4.2", ]
    build_extra_model_and_doc(pro_name, version_list)
    train_random_walk_weight(pro_name, version="v4.2")

    build_method_code_doc(pro_name)
    build_pre_method_code_doc(pro_name)

    train_bm25_method_search_model(pro_name=pro_name)

    for version in version_list:
        train_bm25_graph_sim_model(pro_name=pro_name, version=version)


def train_random_walk_weight(pro_name, version):
    builder = CodeGraphBuilder()
    builder.generate_random_walk_weight(pro_name=pro_name, version=version)


@catch_exception
def cache_wikidata_item_and_title_search(pro_name):
    builder = CodeGraphBuilder()

    print("start fetch for %r" % pro_name)
    domain_dir = Path(PathUtil.domain_concept_dir(pro_name=pro_name, version="v1"))
    terms = []
    with (domain_dir / "terms.txt").open("r", encoding="utf-8") as f:
        terms = {line.strip() for line in f}

    generic_title_search_cache_path = PathUtil.generic_title_search_cache()
    generic_wikidata_item_cache_path = PathUtil.generic_wikidata_item_cache()

    project_title_search_cache_path = PathUtil.project_title_search_cache(pro_name)
    project_wikidata_item_cache_path = PathUtil.project_wikidata_item_cache(pro_name)
    builder.cache_wikidata_and_title_search_for_v3(pro_name=pro_name, terms=terms,
                                                   project_wikidata_item_cache_path=project_wikidata_item_cache_path,
                                                   project_title_search_cache_path=project_title_search_cache_path,
                                                   generic_wikidata_item_cache_path=generic_wikidata_item_cache_path,
                                                   generic_title_search_cache_path=generic_title_search_cache_path

                                                   )


if __name__ == "__main__":
    build_jdk_all_graph_and_doc()
    # build_android_all_graph_and_doc()
    #
    # pro_list = SUPPORT_PROJECT_LIST
    # # pool = multiprocessing.Pool(processes=len(SUPPORT_PROJECT_LIST))
    # #
    # # for pro_name in pro_list:
    # #     pool.apply_async(build_project_all_graph_and_doc, (pro_name,))
    # #
    # # pool.close()
    # # pool.join()
    # for pro_name in pro_list:
    #     build_project_all_graph_and_doc(pro_name, )
