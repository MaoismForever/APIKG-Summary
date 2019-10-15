import json
import pickle
from pathlib import Path

from sekg.ir.models.compound import CompoundSearchModel
from sekg.graph.exporter.graph_data import GraphData
from definitions import OUTPUT_DIR, ROOT_DIR
from util.path_util import PathUtil


class Summary:
    class_or_method_2_sentence_ids = {}
    sorted_method_and_sentence_id_dict = {}
    all_class_summary = {}
    sort_method_ids = []
    sort_sentence_ids = []

    def __init__(self):
        graph_data_path = PathUtil.graph_data(pro_name="jdk8", version="v3")
        self.graph_data: GraphData = GraphData.load(graph_data_path)
        model_dir = Path(OUTPUT_DIR) / "search_model" / "compound_bm25+avg_n2v"
        self.model = self.create_search_model(model_dir)
        print("It's ok for init!")

    def get_sentence_from_class_or_method(self, id):
        try:
            sentence_id_list = []
            relations = self.graph_data.get_all_out_relations(id)
            for re in relations:
                if re[1] == "has sentence":
                    sentence_id = re[2]
                    sentence_id_list.append(sentence_id)
            return sentence_id_list
        except Exception as e:
            print("exception:" + str(e))
            return None

    def get_method_id_from_class(self, class_id):
        try:
            method_id_list = []
            relations = self.graph_data.get_all_in_relations(class_id)
            method_relation_class = ["belong to"]
            for re in relations:
                if re[1] in method_relation_class:
                    method_id = re[0]
                    if method_id == class_id:
                        method_id = re[2]
                    node_dict = self.graph_data.get_node_info_dict(method_id)
                    if "method" in node_dict["labels"] and "construct method" not in node_dict["labels"]:
                        method_id_list.append(method_id)
            return method_id_list
        except Exception as e:
            print("exception:" + str(e))
            return None

    def get_one_class_or_method_2_sentence(self, query, name, valid_sentence_id_set, class_or_method_2_sentence,
                                           judge):
        count = 1
        class_or_method_2_sentence[name]['sentence'] = []
        class_or_method_2_sentence[name]['url'] = ''
        if judge == 0:
            class_or_method_2_sentence[name]['url'] = 'https://docs.oracle.com/javase/8/docs/api'
            split_name = name.split('.')
            for key in split_name:
                class_or_method_2_sentence[name]['url'] += '/' + key
            class_or_method_2_sentence[name]['url'] += '.html'
        sorted_sentence_ids = self.model.search(query, 10, valid_sentence_id_set)
        for sentence_id in sorted_sentence_ids:
            class_or_method_2_sentence[name]['sentence'].append(sentence_id.doc_name)
            count = count + 1
            if count > 2:
                break
        return class_or_method_2_sentence

    def sorted_method_and_sentence_id(self, method_ids, query, class_id, class_name):
        count = 1
        class_or_method_2_sentence_list = []
        class_or_method_2_sentence = {}
        valid_sentence_id_set = set()
        class_or_method_2_sentence[class_name] = {}
        for sentence_id in self.get_sentence_from_class_or_method(class_id):
            valid_sentence_id_set.add(sentence_id)
        self.get_one_class_or_method_2_sentence(query, class_name, valid_sentence_id_set, class_or_method_2_sentence, 0)
        class_or_method_2_sentence_list.append(class_or_method_2_sentence)
        sorted_method_ids = self.model.search(query, 10, set(method_ids))
        class_name += '.'
        for method_id in sorted_method_ids:
            class_or_method_2_sentence = {}
            valid_sentence_id_set = set(self.get_sentence_from_class_or_method(method_id.doc_id))
            method_name = method_id.doc_name
            try:
                method_name = method_name.split(class_name)[1]
            except Exception as e:
                pass
            class_or_method_2_sentence[method_name] = {}
            self.get_one_class_or_method_2_sentence(query, method_name, valid_sentence_id_set,
                                                    class_or_method_2_sentence,
                                                    1)
            count = count + 1
            class_or_method_2_sentence_list.append(class_or_method_2_sentence)
            if count > 3:
                break
        return class_or_method_2_sentence_list

    def get_summary(self, query, class_name):
        class_node_dict = self.graph_data.find_one_node_by_property('qualified_name', class_name)
        class_id = class_node_dict['id']
        method_id_list_2_class = self.get_method_id_from_class(class_id)
        class_or_method_2_sentence = self.sorted_method_and_sentence_id(method_id_list_2_class, query,
                                                                        class_id, class_name)
        return class_or_method_2_sentence

    @staticmethod
    def create_search_model(model_dir):
        sub_search_model_config_path = model_dir / "submodel.config"
        with open(sub_search_model_config_path, 'rb') as aq:
            sub_search_model_config = pickle.loads(aq.read())
        model_1 = Path(ROOT_DIR) / "output" / "search_model" / "bm25"
        model_2 = Path(ROOT_DIR) / "output" / "search_model" / "avg_n2v"
        new_sub_search_model_config = [
            (model_1, sub_search_model_config[0][1], sub_search_model_config[0][2], sub_search_model_config[0][3]),
            (model_2, sub_search_model_config[1][1], sub_search_model_config[1][2], sub_search_model_config[1][3]),
        ]
        with open(sub_search_model_config_path, 'wb') as out:
            out.write(pickle.dumps(new_sub_search_model_config))
        model = CompoundSearchModel.load(model_dir)
        return model

    @staticmethod
    def get_test_data(path):
        try:
            with open(path, 'rb') as json_file:
                load_dict = json.load(json_file)
                json_file.close()
            return load_dict
        except Exception as e:
            print("exception:" + str(e))

    def get_summary_only_query(self, query, number):
        all_class_2_summary = {}
        class_id_2_method_ids = {}
        class_and_method_ids = []
        method_and_sentence_ids = []
        valid_class_ids = self.graph_data.get_node_ids_by_label("class")
        sorted_class_ids = self.model.search(query, number, valid_class_ids)
        for sorted_class_id in sorted_class_ids:
            class_id = sorted_class_id.doc_id
            class_and_method_ids.append(class_id)
            class_id_2_method_ids[class_id] = self.get_method_id_from_class(class_id)
            method_and_sentence_ids += class_id_2_method_ids[class_id]
            class_and_method_ids += class_id_2_method_ids[class_id]
        for class_or_method_id in class_and_method_ids:
            self.class_or_method_2_sentence_ids[class_or_method_id] = self.get_sentence_from_class_or_method(
                class_or_method_id)
            method_and_sentence_ids += self.class_or_method_2_sentence_ids[class_or_method_id]
        sorted_method_and_sentence_ids = self.model.search(query, len(method_and_sentence_ids), method_and_sentence_ids)
        number = 1
        for item in sorted_method_and_sentence_ids:
            self.sorted_method_and_sentence_id_dict[item.doc_id] = number
            number += 1
        index = 0
        for class_id in list(class_id_2_method_ids.keys()):
            all_class_2_summary[index] = []
            class_node = self.graph_data.find_nodes_by_ids(class_id)
            class_name = class_node[0]['properties']['qualified_name']
            class_name_1 = class_name + '.'
            method_num_2_id = {}
            method_nums = []
            method_ids = class_id_2_method_ids[class_id]
            class_or_method_2_sentence = {class_name: {}}
            class_or_method_2_sentence[class_name]['url'] = 'https://docs.oracle.com/javase/8/docs/api'
            split_name = class_name.split('.')
            for key in split_name:
                class_or_method_2_sentence[class_name]['url'] += '/' + key
            class_or_method_2_sentence[class_name]['url'] += '.html'
            class_or_method_2_sentence[class_name]['sentence'] = []
            self.create_class_or_method_2_sentence(class_id, class_name, class_or_method_2_sentence)
            all_class_2_summary[index].append(class_or_method_2_sentence)
            for method_id in method_ids:
                method_num_2_id[self.sorted_method_and_sentence_id_dict[method_id]] = method_id
                method_nums.append(self.sorted_method_and_sentence_id_dict[method_id])
            method_nums.sort()
            if len(method_nums) > 3:
                count_method = 0
                for method_num in method_nums:
                    if count_method >= 3:
                        break
                    count_method += 1
                    method_id = method_num_2_id[method_num]
                    method_node = self.graph_data.find_nodes_by_ids(method_id)
                    method_name = method_node[0]['properties']['qualified_name']
                    method_name = method_name.split(class_name_1)[1]
                    class_or_method_2_sentence = {method_name: {}}
                    class_or_method_2_sentence[method_name]['url'] = ''
                    self.create_class_or_method_2_sentence(method_id, method_name, class_or_method_2_sentence)
                    all_class_2_summary[index].append(class_or_method_2_sentence)
            else:
                for method_num in method_nums:
                    method_id = method_num_2_id[method_num]
                    method_node = self.graph_data.find_nodes_by_ids(method_id)
                    method_name = method_node[0]['properties']['qualified_name']
                    method_name = method_name.split(class_name_1)[1]
                    class_or_method_2_sentence = {method_name: {}}
                    class_or_method_2_sentence[method_name]['url'] = ''
                    self.create_class_or_method_2_sentence(method_id, method_name, class_or_method_2_sentence)
                    all_class_2_summary[index].append(class_or_method_2_sentence)
            index += 1
        return all_class_2_summary

    def create_class_or_method_2_sentence(self, class_or_method_id, name, class_or_method_2_sentence):
        class_or_method_2_sentence[name]['sentence'] = []
        sentence_num_2_id = {}
        sentence_nums = []
        for sentence_id in self.class_or_method_2_sentence_ids[class_or_method_id]:
            sentence_num_2_id[self.sorted_method_and_sentence_id_dict[sentence_id]] = sentence_id
            sentence_nums.append(self.sorted_method_and_sentence_id_dict[sentence_id])
        sentence_nums.sort()
        if len(sentence_nums) > 3:
            count_sentence = 0
            for sentence_num in sentence_nums:
                if count_sentence >= 3:
                    break
                count_sentence += 1
                sentence_id = sentence_num_2_id[sentence_num]
                sentence_name = self.graph_data.find_nodes_by_ids(sentence_id)[0]['properties']['sentence_name']
                class_or_method_2_sentence[name]['sentence'].append(sentence_name)
        else:
            for sentence_num in sentence_nums:
                sentence_id = sentence_num_2_id[sentence_num]
                sentence_name = self.graph_data.find_nodes_by_ids(sentence_id)[0]['properties']['sentence_name']
                class_or_method_2_sentence[name]['sentence'].append(sentence_name)

    def get_summary_only_query_by_sentence(self, query, number):
        method_ids = []
        class_ids = []
        count = 0
        all_method_ids = self.graph_data.get_node_ids_by_label("method")
        constructor_method_ids = self.graph_data.get_node_ids_by_label("construct method")
        valid_method_ids = all_method_ids - constructor_method_ids
        sort_method_document_ids = self.model.search(query, len(valid_method_ids), valid_method_ids)
        for item in sort_method_document_ids:
            self.sort_method_ids.append(item.doc_id)
        valid_sentence_ids = self.graph_data.get_node_ids_by_label("sentence")
        sort_sentence_document_ids = self.model.search(query, len(valid_sentence_ids), valid_sentence_ids)
        for item in sort_sentence_document_ids:
            self.sort_sentence_ids.append(item.doc_id)
        for sentence_id in self.sort_sentence_ids:
            if count >= number:
                break
            method_ids_by_sentence_id = self.get_method_ids_sort_by_sentence_id(sentence_id, method_ids)
            method_ids += method_ids_by_sentence_id
            for method_id in method_ids_by_sentence_id:
                class_id = self.get_class_id_from_method(method_id)
                if class_id not in class_ids:
                    if count >= number:
                        break
                    class_ids.append(class_id)
                    self.get_single_summary(class_id, count)
                    count += 1
        return self.all_class_summary

    def get_method_ids_sort_by_sentence_id(self, sentence_id, have_method_ids=[]):
        try:
            method_ids = []
            relations = self.graph_data.get_all_in_relations(sentence_id)
            method_relation_class = ["has sentence"]
            for re in relations:
                if re[1] in method_relation_class:
                    method_id = re[0]
                    if sentence_id == method_id:
                        method_id = re[0]
                    if method_id not in self.sort_method_ids or method_id in have_method_ids:
                        continue
                    method_ids.append(method_id)
            return method_ids
        except Exception as e:
            print("exception:" + str(e))
            return -1

    def get_summary_only_query_by_method(self, query, number):
        class_ids = []
        count = 0
        all_method_ids = self.graph_data.get_node_ids_by_label("method")
        constructor_method_ids = self.graph_data.get_node_ids_by_label("construct method")
        valid_method_ids = all_method_ids - constructor_method_ids
        sort_method_document_ids = self.model.search(query, len(valid_method_ids), valid_method_ids)
        for item in sort_method_document_ids:
            self.sort_method_ids.append(item.doc_id)
        valid_sentence_ids = self.graph_data.get_node_ids_by_label("sentence")
        sort_sentence_document_ids = self.model.search(query, len(valid_sentence_ids), valid_sentence_ids)
        for item in sort_sentence_document_ids:
            self.sort_sentence_ids.append(item.doc_id)
        for method_id in self.sort_method_ids:
            class_id = self.get_class_id_from_method(method_id)
            if class_id not in class_ids:
                if count >= number:
                    break
                class_ids.append(class_id)
                self.get_single_summary(class_id, count)
                count += 1
        return self.all_class_summary

    def get_single_summary(self, class_id, count=0):
        self.all_class_summary[count] = []
        class_2_method_ids = self.get_method_id_from_class(class_id)
        class_2_sentence_ids = self.get_sentence_from_class_or_method(class_id)
        class_node = self.graph_data.find_nodes_by_ids(class_id)
        class_name = class_node[0]['properties']['qualified_name']
        class_name_need_2_split = class_name + '.'
        class_2_sentence = {class_name: {}}
        class_2_sentence[class_name]['url'] = 'https://docs.oracle.com/javase/8/docs/api'
        split_name = class_name.split('.')
        for key in split_name:
            class_2_sentence[class_name]['url'] += '/' + key
        class_2_sentence[class_name]['url'] += '.html'
        class_2_sentence[class_name]['sentence'] = []
        class_2_sentence = self.get_sentence_sort(class_2_sentence_ids, class_name, class_2_sentence)
        self.all_class_summary[count].append(class_2_sentence)
        class_method_dict_rank = {}
        method_rank_list = []
        for method_id in class_2_method_ids:
            class_method_dict_rank[self.sort_method_ids.index(method_id)] = method_id
            method_rank_list.append(self.sort_method_ids.index(method_id))
        method_rank_list.sort()
        if len(method_rank_list) > 3:
            method_num = 3
        else:
            method_num = len(method_rank_list)
        for method_num in range(method_num):
            method_id = class_method_dict_rank[method_rank_list[method_num]]
            method_node = self.graph_data.find_nodes_by_ids(method_id)
            method_name = method_node[0]['properties']['qualified_name']
            method_name = method_name.split(class_name_need_2_split)[1]
            method_2_sentence = {method_name: {}}
            method_2_sentence[method_name]['url'] = ''
            method_2_sentence[method_name]['sentence'] = []
            method_2_sentence_ids = self.get_sentence_from_class_or_method(method_id)
            method_2_sentence = self.get_sentence_sort(method_2_sentence_ids, method_name, method_2_sentence)
            self.all_class_summary[count].append(method_2_sentence)

    def get_sentence_sort(self, class_or_method_2_sentence_ids, class_or_method_name, class_or_method_2_sentence):
        class_or_method_sentence_dict_rank = {}
        sentence_rank_list = []
        for sentence_id in class_or_method_2_sentence_ids:
            class_or_method_sentence_dict_rank[self.sort_sentence_ids.index(sentence_id)] = sentence_id
            sentence_rank_list.append(self.sort_sentence_ids.index(sentence_id))
        sentence_rank_list.sort()
        if len(sentence_rank_list) > 3:
            sentence_num = 3
        else:
            sentence_num = len(sentence_rank_list)
        for num in range(sentence_num):
            sentence_name = self.graph_data.find_nodes_by_ids(class_or_method_sentence_dict_rank[sentence_rank_list[num]])[0]['properties']['sentence_name']
            class_or_method_2_sentence[class_or_method_name]['sentence'].append(sentence_name)
        return class_or_method_2_sentence

    def get_class_id_from_method(self, method_id):
        try:
            class_id = -1
            relations = self.graph_data.get_all_out_relations(method_id)
            method_relation_class = ["belong to"]
            for re in relations:
                if re[1] in method_relation_class:
                    class_id = re[2]
                    if method_id == class_id:
                        class_id = re[0]
                    node_dict = self.graph_data.get_node_info_dict(class_id)
                    if "class" in node_dict["labels"]:
                        return class_id
            return class_id
        except Exception as e:
            print("exception:" + str(e))
            return -1
