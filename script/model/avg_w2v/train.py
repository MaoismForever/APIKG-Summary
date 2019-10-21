from pathlib import Path

from sekg.ir.doc.wrapper import PreprocessMultiFieldDocumentCollection, MultiFieldDocumentCollection
from sekg.ir.models.avg_w2v import AVGW2VFLModel
from sekg.ir.models.n2v.svm.avg_n2v import AVGNode2VectorModel
from sekg.ir.preprocessor.base import Preprocessor
from sekg.ir.preprocessor.code_text import CodeDocPreprocessor
from sekg.util.annotation import catch_exception

from definitions import SUPPORT_PROJECT_LIST, DATA_DIR
from util.path_util import PathUtil


@catch_exception
def train_avg_w2v_model(pro_name, version):
    doc_path = PathUtil.doc(pro_name, version)
    collection = MultiFieldDocumentCollection.load(str(doc_path))
    processor = CodeDocPreprocessor()
    pre_doc_collection = PreprocessMultiFieldDocumentCollection.create_from_doc_collection(processor, collection)

    word2vec_model_path = PathUtil.sim_model(pro_name=pro_name, version=version, model_type="avg_w2v")
    AVGW2VFLModel.train(model_dir_path=word2vec_model_path,
                        doc_collection=pre_doc_collection)
    return word2vec_model_path


if __name__ == '__main__':
    pro_list = SUPPORT_PROJECT_LIST
    versions = ["v3_1"]
    for version in versions:
        for pro_name in pro_list:
            train_avg_w2v_model(pro_name, version)
