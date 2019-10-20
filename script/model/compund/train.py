from pathlib import Path

from sekg.ir.doc.wrapper import PreprocessMultiFieldDocumentCollection, MultiFieldDocumentCollection
from sekg.ir.models.bm25 import BM25Model
from sekg.ir.models.compound import CompoundSearchModel
from sekg.ir.models.n2v.svm.avg_n2v import AVGNode2VectorModel
from sekg.ir.models.n2v.svm.tfidf_n2v import TFIDFNode2VectorModel
from sekg.ir.models.tf_idf import TFIDFModel
from sekg.ir.preprocessor.base import Preprocessor
from sekg.ir.preprocessor.code_text import CodeDocPreprocessor

from definitions import SUPPORT_PROJECT_LIST, DATA_DIR, OUTPUT_DIR
from util.annotation import catch_exception
from util.path_util import PathUtil


@catch_exception
def train_model(pro_name, version, first_model_config, second_model_config):
    document_collection_path = PathUtil.doc("jdk8", "v4")
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
    pro_list = SUPPORT_PROJECT_LIST
    versions = ["v3_1"]
    for version in versions:
        for pro_name in pro_list:
            model_compound_list = [
                # [("tfidf", TFIDFModel, 0.6), ("tfidf_n2v", TFIDFNode2VectorModel, 0.4)],
                [("bm25", BM25Model, 0.6), ("avg_n2v", AVGNode2VectorModel, 0.4)]

            ]
            for model_compound_info in model_compound_list:
                train_model(pro_name, version, first_model_config=model_compound_info[0],
                            second_model_config=model_compound_info[1])
