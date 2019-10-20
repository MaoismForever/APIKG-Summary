from pathlib import Path

from sekg.ir.doc.wrapper import PreprocessMultiFieldDocumentCollection, MultiFieldDocumentCollection
from sekg.ir.models.n2v.svm.avg_n2v import AVGNode2VectorModel
from sekg.ir.preprocessor.base import Preprocessor
from sekg.ir.preprocessor.code_text import CodeDocPreprocessor
from sekg.util.annotation import catch_exception

from definitions import SUPPORT_PROJECT_LIST, DATA_DIR
from util.path_util import PathUtil


@catch_exception
def train_model(pro_name, version, weight):
    # pre_doc_collection_out_path = PathUtil.pre_doc(pro_name, version, pre_way="spacy-pre")
    # document_collection_path = Path(DATA_DIR) / 'doc' / 'jdk8' / 'jdk8.v4.dc'
    document_collection_path = PathUtil.doc(pro_name, version)
    collection = MultiFieldDocumentCollection.load(str(document_collection_path))
    processor = CodeDocPreprocessor()
    doc_collection = PreprocessMultiFieldDocumentCollection.create_from_doc_collection(processor, collection)

    graph_data_path = PathUtil.graph_data(pro_name=pro_name, version=version)

    pretrain_node2vec_path = PathUtil.node2vec(pro_name=pro_name, version=version, weight=weight)

    # doc_collection: PreprocessMultiFieldDocumentCollection = PreprocessMultiFieldDocumentCollection.load(
    #     pre_doc_collection_out_path)

    embedding_size = 100

    kg_name_searcher_path = PathUtil.name_searcher(pro_name=pro_name, version=version)

    model_dir_path = PathUtil.sim_model(pro_name=pro_name, version=version, model_type="avg_n2v")
    model = AVGNode2VectorModel.train(model_dir_path=model_dir_path,
                                      doc_collection=doc_collection,
                                      embedding_size=embedding_size,
                                      pretrain_node2vec_path=pretrain_node2vec_path,
                                      graph_data_path=graph_data_path,
                                      kg_name_searcher_path=kg_name_searcher_path,
                                      )
    return model_dir_path


if __name__ == '__main__':
    pro_list = SUPPORT_PROJECT_LIST
    weights = ["unweight"]
    versions = ["v3_1"]
    for version in versions:
        for pro_name in pro_list:
            for weight in weights:
                train_model(pro_name, version, weight)
