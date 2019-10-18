from pathlib import Path

from sekg.ir.doc.wrapper import PreprocessMultiFieldDocumentCollection, MultiFieldDocumentCollection
from sekg.ir.models.n2v.svm.avg_n2v import AVGNode2VectorModel
from sekg.ir.preprocessor.base import Preprocessor
from sekg.util.annotation import catch_exception
from sekg.ir.models.bm25 import BM25Model

from definitions import SUPPORT_PROJECT_LIST, DATA_DIR
from util.path_util import PathUtil


@catch_exception
def train_model(pro_name, version):
    # pre_doc_collection_out_path = PathUtil.pre_doc(pro_name, version, pre_way="spacy-pre")
    # document_collection_path = Path(DATA_DIR) / 'doc' / 'jdk8' / 'jdk8.v4.dc'
    document_collection_path = PathUtil.doc(pro_name, version)
    collection = MultiFieldDocumentCollection.load(str(document_collection_path))
    processor = Preprocessor()
    doc_collection = PreprocessMultiFieldDocumentCollection.create_from_doc_collection(processor, collection)
    model_dir_path = PathUtil.sim_model(pro_name=pro_name, version=version, model_type="bm25")
    BM25Model.train(model_dir_path, doc_collection=doc_collection)
    return model_dir_path


if __name__ == '__main__':
    pro_list = SUPPORT_PROJECT_LIST
    versions = ["v3"]
    for version in versions:
        for pro_name in pro_list:
            train_model(pro_name, version)
