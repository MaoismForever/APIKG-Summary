import sys
sys.path.append('/home/fdse/lvgang/APIKGSummaryV1')
from pathlib import Path

from sekg.ir.doc.wrapper import PreprocessMultiFieldDocumentCollection
from sekg.model.word2vec.tune_word2vec import TunedWord2VecTrainer
from sekg.util.annotation import catch_exception

from definitions import SUPPORT_PROJECT_LIST
from util.path_util import PathUtil


@catch_exception
def train_tune_word_embedding(pro_name, version, pre_way="code-pre"):
    pretrain_w2v_path = PathUtil.pretrain_wiki_w2v()

    trainer = TunedWord2VecTrainer()
    pre_doc_collection_out_path = PathUtil.pre_doc(pro_name=pro_name, version=version, pre_way=pre_way)
    preprocess_doc_collection: PreprocessMultiFieldDocumentCollection = PreprocessMultiFieldDocumentCollection.load(
        pre_doc_collection_out_path)

    corpus = []
    preprocess_multi_field_doc_list = preprocess_doc_collection.get_all_preprocess_document_list()
    for docno, multi_field_doc in enumerate(preprocess_multi_field_doc_list):
        corpus.append(multi_field_doc.get_document_text_words())

    print("Start training embedding...")

    w2v = trainer.tune(corpus=corpus, pretrain_w2v_path=pretrain_w2v_path, pretrain_binary=True, window=5)

    w2v.wv.save(PathUtil.tuned_word2vec(pro_name, version=version))


if __name__ == "__main__":
    pro_list = SUPPORT_PROJECT_LIST
    versions = ["v1", "v2", "v3"]
    for pro_name in pro_list:
        for version in versions:
            train_tune_word_embedding(pro_name, version=version)
