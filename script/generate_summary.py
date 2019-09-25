import json
import time
from json import dumps
from pathlib import Path
import sys

from flask import jsonify
from sekg.ir.models.compound import CompoundSearchModel
from sekg.ir.models.n2v.svm.avg_n2v import AVGNode2VectorModel

sys.path.append('/home/fdse/lvgang/APIKGSummaryV1')
from sekg.graph.exporter.graph_data import GraphData
from sekg.ir.models.bm25 import BM25Model
from sekg.ir.models.tf_idf import TFIDFModel

from definitions import OUTPUT_DIR
from util.path_util import PathUtil


def get_sentence_from_class_or_method(graph_data: GraphData, id):
    try:
        sectence_id_list = []
        relations = graph_data.get_all_out_relations(id)
        for re in relations:
            if re[1] == "has sentence":
                sentence_id = re[2]
                sectence_id_list.append(sentence_id)
        return sectence_id_list
    except Exception as e:
        print("exception:" + str(e))
        return None


def get_method_id_from_class(graph_data: GraphData, class_id):
    try:
        method_id_list = []
        method_id_type = [7, 11, 17]
        relations = graph_data.get_all_in_relations(class_id)
        # 可以以后再增加关系
        # method_relation_class = ["belong to", "thrown exception type", "return value type"]
        method_relation_class = ["belong to"]
        for re in relations:
            if re[1] in method_relation_class:
                method_id = re[0]
                if method_id == class_id:
                    method_id = re[2]
                node_dict = graph_data.get_node_info_dict(method_id)
                id_type = -2
                try:
                    id_type = node_dict['properties']['api_type']
                except Exception as e:
                    try:
                        id_type = node_dict['properties']['entity_category']
                    except Exception as e:
                        continue
                if id_type in method_id_type:
                    method_id_list.append(method_id)
        return method_id_list
    except Exception as e:
        print("exception:" + str(e))
        return None


def get_one_class_or_method_2_sentence(query, name, valid_sentence_id_set, class_or_method_2_sentence,
                                       model: CompoundSearchModel, judge):
    """
    得到每个方法或类最相似的句子
    :param query:
    :param model:
    :param name:
    :param valid_sentence_id_set:
    :param class_or_method_2_sentence:
    :return:
    """
    count = 1
    class_or_method_2_sentence[name]['sentence'] = []
    class_or_method_2_sentence[name]['url'] = ''
    if judge == 0:
        class_or_method_2_sentence[name]['url'] = 'https://docs.oracle.com/javase/8/docs/api'
        split_name = name.split('.')
        for key in split_name:
            class_or_method_2_sentence[name]['url'] += '/' + key
        class_or_method_2_sentence[name]['url'] += '.html'
    sorted_sentence_ids = model.search(query, 10, valid_sentence_id_set)
    for sentence_id in sorted_sentence_ids:
        class_or_method_2_sentence[name]['sentence'].append(sentence_id.doc_name)
        count = count + 1
        if count > 2:
            break
    return class_or_method_2_sentence


def sorted_method_and_sentence_id(graph_data: GraphData, model: CompoundSearchModel, method_ids, query, class_id, class_name):
    """
    :return:
    dict{
        class_name: sentence_names,
        method_name_1: sentence_names,
        method_name_2: sentence_names,
        method_name_3: sentence_names
    }
    """
    count = 1
    class_or_method_2_sentence_list = []
    class_or_method_2_sentence = {}
    valid_sentence_id_set = set()
    class_or_method_2_sentence[class_name] = {}
    for sentence_id in get_sentence_from_class_or_method(graph_data, class_id):
        valid_sentence_id_set.add(sentence_id)
    get_one_class_or_method_2_sentence(query, class_name, valid_sentence_id_set, class_or_method_2_sentence, model, 0)
    class_or_method_2_sentence_list.append(class_or_method_2_sentence)
    # 得到前十个最相似的方法
    sorted_method_ids = model.search(query, 10, set(method_ids))
    class_name += '.'
    for method_id in sorted_method_ids:
        class_or_method_2_sentence = {}
        valid_sentence_id_set = set(get_sentence_from_class_or_method(graph_data, method_id.doc_id))
        method_name = method_id.doc_name
        try:
            method_name = method_name.split(class_name)[1]
        except:
            pass
        class_or_method_2_sentence[method_name] = {}
        get_one_class_or_method_2_sentence(query, method_name, valid_sentence_id_set, class_or_method_2_sentence, model,
                                           1)
        count = count + 1
        class_or_method_2_sentence_list.append(class_or_method_2_sentence)
        if count > 3:
            break
    return class_or_method_2_sentence_list


def get_summary(graph_data: GraphData, query, model: CompoundSearchModel, class_name):
    """
    input : query + class
    :param graph_data:
    :param query:
    :param class_name:
    :param model:
    :return:
    """
    class_node_dict = graph_data.find_one_node_by_property('qualified_name', class_name)
    class_id = class_node_dict['id']
    method_id_list_2_class = get_method_id_from_class(graph_data, class_id)
    class_or_method_2_sentence = sorted_method_and_sentence_id(graph_data, model, method_id_list_2_class, query,
                                                               class_id, class_name)
    return class_or_method_2_sentence


def create_search_model(model_dir):
    model = CompoundSearchModel.load(model_dir)
    # model = AVGNode2VectorModel.load(model_dir)
    return model


def get_test_data(path):
    try:
        with open(path, 'rb') as json_file:
            load_dict = json.load(json_file)
            json_file.close()
        return load_dict
    except Exception as e:
        print("exception:" + str(e))


def get_summary_only_query(graph_data: GraphData, query, model: CompoundSearchModel, number):
    """

    :param graph_data: 所有图的节点
    :param query: 输入的问题
    :param model: 训练的模型
    :param number: 需要搜寻的类数
    :return:
    """
    start_time = time.time()
    all_class_2_summary = {}
    valid_class_ids = graph_data.get_node_ids_by_label("class")
    sorted_class_ids = model.search(query, number, valid_class_ids)
    index = 0
    for sorted_class_id in sorted_class_ids:
        class_name = sorted_class_id.doc_name
        class_summary = get_summary(graph_data, query, model, class_name)
        all_class_2_summary[index] = class_summary
        index += 1
    end_time = time.time()
    print("time ", (end_time - start_time))
    return all_class_2_summary


if __name__ == '__main__':
    graph_data_path = PathUtil.graph_data(pro_name="jdk8", version="v3")
    graph_data: GraphData = GraphData.load(graph_data_path)
    # model_dir = Path(OUTPUT_DIR) / "search_model" / "avg_n2v"
    # model_name = "avg_n2v"
    model_dir = Path(OUTPUT_DIR) / "search_model" / "compound_bm25+avg_n2v"
    model_name = "compound_bm25+avg_n2v"
    model = create_search_model(model_dir)
    print("------The model is", model_name, "------")
    # test_data_path = Path(OUTPUT_DIR) / "test_data" / "query_for_experiment.json"
    # biker_data = get_test_data(test_data_path)
    # all_result = []
    # number = 0
    # total_length = len(biker_data)
    # for data in biker_data:
    #     query = data['query']
    #     sub_length = len(data['class'])
    #     number += 1
    #     sub_number = 0
    #     for class_name in data['class']:
    #         sub_number += 1
    #         current_length = str(number) + "." + str(sub_number)
    #         print("主问题总数为%d，目前主问题的子问题总数为%d，现在正在处理%s" % (total_length, sub_length, current_length))
    #         class_or_method_2_sentence = get_summary(graph_data, query, model, class_name)
    #         all_result.append(class_or_method_2_sentence)
    # result_path = Path(OUTPUT_DIR) / "test_data" / "new_result_for_experiment.json"
    # with open(result_path, 'w', encoding='utf-8') as json_file:
    #     json.dump(all_result, json_file, ensure_ascii=False)
    # class_name = "java.lang.Thread"
    # query = "How to wait for all threads to finish, using ExecutorService?"
    # get_summary(graph_data, query, model, class_name)
    query = "How do I properly load a BufferedImage in java?"
    get_summary_only_query(graph_data, query, model, 20)
