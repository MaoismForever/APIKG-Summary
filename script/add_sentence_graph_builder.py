import sys
from pathlib import Path
from definitions import OUTPUT_DIR
from script.fast_text.fasttext_classifier import FastTextClassifier
from sekg.graph.exporter.graph_data import GraphData
from util.graph_load_util import GraphLoadUtil
from util.import_extract_result_2_graph_data import ExtractResultImport
from util.path_util import PathUtil

pro_list = ["jdk8"]
classifier = FastTextClassifier()

for pro_name in pro_list:
    print("正在处理%s" % pro_name)
    collection = GraphLoadUtil.load_doc(pro_name, "v1")
    docs = collection.get_document_list()

    graph_data_path = PathUtil.graph_data(pro_name=pro_name, version="v1")
    graph_data: GraphData = GraphData.load(graph_data_path)
    new_graph_data_path = PathUtil.graph_data(pro_name=pro_name, version="v2")
    res = ExtractResultImport(graph_data, new_graph_data_path, 2)

    length = len(docs)
    number = 0
    for doc in docs:
        number += 1
        if number % 200 == 1:
            print("总共%d条数据，已执行%d条数据" % (length, number))
        api_id = doc.get_document_id()
        short_descs = doc.get_doc_text_by_field('short_description_sentences')
        for short_desc in short_descs:
            label = list(classifier.predict(short_desc))[0]
            if label == '__label__0':
                print(short_desc)
                filter_sentence_path = str(Path(OUTPUT_DIR) / "graph" / "jdk8" / "filter_data" / "filter_sentence.txt")
                with open(filter_sentence_path, "a") as f:
                    f.write(short_desc)
                    f.write("\n")
                continue
            else:
                res.add_sentence_relation(short_desc, api_id)
    res.save_new_graph_data()
