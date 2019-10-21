from pathlib import Path

from sekg.ir.doc.wrapper import PreprocessMultiFieldDocumentCollection, MultiFieldDocumentCollection
from sekg.ir.models.avg_w2v import AVGW2VFLModel
from sekg.ir.models.bm25 import BM25Model
from sekg.ir.models.compound import CompoundSearchModel
from sekg.ir.models.n2v.svm.avg_n2v import AVGNode2VectorModel
from sekg.ir.models.n2v.svm.filter_semantic_tfidf_n2v import FilterSemanticTFIDFNode2VectorModel
from sekg.ir.models.n2v.svm.tfidf_n2v import TFIDFNode2VectorModel
from sekg.ir.models.tf_idf import TFIDFModel
from sekg.ir.preprocessor.base import Preprocessor
from sekg.ir.preprocessor.code_text import CodeDocPreprocessor

from definitions import SUPPORT_PROJECT_LIST, DATA_DIR, OUTPUT_DIR
from script.model.avg_w2v.train import train_avg_w2v_model
from script.model.n2v.svm_train import SVMTrainer
from util.annotation import catch_exception
from util.path_util import PathUtil


@catch_exception
def train_model(pro_name, version, first_model_config, second_model_config):
    document_collection_path = PathUtil.doc(pro_name, version)
    collection = MultiFieldDocumentCollection.load(str(document_collection_path))
    processor = CodeDocPreprocessor()
    doc_collection = PreprocessMultiFieldDocumentCollection.create_from_doc_collection(processor, collection)

    # pre_doc_collection_out_path = PathUtil.pre_doc(pro_name, version, pre_way="code-pre")
    # doc_collection: PreprocessMultiFieldDocumentCollection = PreprocessMultiFieldDocumentCollection.load(
    #     pre_doc_collection_out_path)

    sub_search_model_config = [
        (PathUtil.sim_model(pro_name=pro_name, version=version, model_type=first_model_config[0]),
         first_model_config[1], first_model_config[2], False),
        (PathUtil.sim_model(pro_name=pro_name, version=version, model_type=second_model_config[0]),
         second_model_config[1], second_model_config[2], True),
    ]

    compound_model_name = "compound_{base_model}+{extra_model}".format(base_model=first_model_config[0],
                                                                       extra_model=second_model_config[0])

    print("try to model compound model for %r" % compound_model_name)

    model_dir_path = PathUtil.sim_model(pro_name=pro_name, version=version, model_type=compound_model_name)

    model = CompoundSearchModel.train(model_dir_path=model_dir_path,
                                      doc_collection=doc_collection,
                                      sub_search_model_config=sub_search_model_config
                                      )

    return model_dir_path


if __name__ == '__main__':
    pro_name = "jdk8"
    version = "v3_1"
    svm = SVMTrainer(pro_name, version)
    svm.train()
    train_avg_w2v_model(pro_name, version)
    model_compound_list = [
        [("avg_w2v", AVGW2VFLModel, 0.6), ("svm", FilterSemanticTFIDFNode2VectorModel, 0.4)]

    ]
    for model_compound_info in model_compound_list:
        train_model(pro_name, version, first_model_config=model_compound_info[0],
                    second_model_config=model_compound_info[1])
