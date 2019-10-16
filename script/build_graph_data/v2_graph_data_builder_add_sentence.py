import sys
from pathlib import Path

from sekg.ir.doc.wrapper import MultiFieldDocumentCollection

from definitions import OUTPUT_DIR
from script.fast_text.fasttext_classifier import FastTextClassifier
from sekg.graph.exporter.graph_data import GraphData
from util.import_extract_result_2_graph_data import ExtractResultImport
from util.path_util import PathUtil

classifier = FastTextClassifier()


def build_v2_graph_for_pro(pro_name):
    document_collection_path = PathUtil.doc(pro_name=pro_name, version="v1")
    collection: MultiFieldDocumentCollection = MultiFieldDocumentCollection.load(document_collection_path)
    docs = collection.get_document_list()

    graph_data_path = PathUtil.graph_data(pro_name=pro_name, version="v1")
    graph_data: GraphData = GraphData.load(graph_data_path)
    new_graph_data_path = PathUtil.graph_data(pro_name=pro_name, version="v2")
    res = ExtractResultImport(graph_data, new_graph_data_path, 2)
    for doc in docs:
        api_id = doc.get_document_id()
        short_descs = doc.get_doc_text_by_field('short_description_sentences')
        for short_desc in short_descs:
            label = list(classifier.predict(short_desc))[0]
            if label == '__label__0':
                print(short_desc)
                filter_sentence_path = str(
                    Path(OUTPUT_DIR) / "graph" / "jdk8" / "filter_data" / "filter_sentence.txt")
                with open(filter_sentence_path, "a") as f:
                    f.write(short_desc)
                    f.write("\n")
                continue
            else:
                res.add_sentence_relation(short_desc, api_id)
    res.save_new_graph_data()


if __name__ == '__main__':
    pro_list = ["jdk8"]
    build_v2_graph_for_pro(pro_list[0])
