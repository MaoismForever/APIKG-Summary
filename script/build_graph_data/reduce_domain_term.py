from pathlib import Path
from sekg.ir.doc.wrapper import PreprocessMultiFieldDocumentCollection
from sekg.ir.preprocessor.code_text import CodeDocPreprocessor
from sekg.util.code import ConceptElementNameUtil
from util.data_util import EntityReader
from util.path_util import PathUtil
from gensim.corpora.dictionary import Dictionary


class ReduceDomainTerm:
    def __init__(self, term_save_path, operation_save_path, term_relation_save_path, linkage_save_path,
                 aliase_save_path, pre_doc_collection_out_path):
        self.terms = EntityReader.read_line_data(term_save_path)
        # self.operations = EntityReader.read_line_data(operation_save_path)
        self.relations = EntityReader.read_json_data(term_relation_save_path)
        self.linkages = EntityReader.read_json_data(linkage_save_path)
        self.aliases_map = EntityReader.read_json_data(aliase_save_path)
        self.pre_doc_collection_out_path = pre_doc_collection_out_path
        self.uncamel_util = ConceptElementNameUtil()
        self.code_pre = CodeDocPreprocessor()
        self.all_words = {}
        self.uncamel_map = {}

        self.start_relation = {}
        self.end_relation = {}
        self.all_relation = {}

        self.start_record_for_linkage = {}
        self.end_record_for_linkage = {}
        self.start_with_r_record = {}
        self.end_with_r_record = {}
        self.mention_time = {}
        self.operation_time = {}
        self.represent_time = {}
        self.instance_of_time = {}
        self.end_related_relation_num = {}

        self.sum_mention_time = {}

        self.init_cal()
        self.count_all_word()

    def init_cal(self):
        for start, r, end in self.relations:
            self.start_relation[start] = self.start_relation.get(start, 0) + 1
            self.end_relation[end] = self.end_relation.get(end, 0) + 1
            self.all_relation[start] = self.all_relation.get(start, 0) + 1
            self.all_relation[end] = self.all_relation.get(end, 0) + 1

        for start, r, end in self.linkages:
            start = str(start)
            end = str(end)
            self.start_record_for_linkage[start] = self.start_record_for_linkage.get(start, 0) + 1
            self.end_record_for_linkage[end] = self.end_record_for_linkage.get(end, 0) + 1
            self.start_with_r_record[start + "_" + r] = self.start_with_r_record.get(start + "_" + r, 0) + 1
            self.end_with_r_record[end + "_" + r] = self.end_with_r_record.get(end + "_" + r, 0) + 1
            if r.startswith("mention"):
                self.mention_time[end] = self.mention_time.get(end, 0) + 1
            if r.startswith("operation"):
                self.operation_time[end] = self.operation_time.get(end, 0) + 1
            if r.startswith("instance of"):
                self.instance_of_time[end] = self.instance_of_time.get(end, 0) + 1
            if r.startswith("represent"):
                self.represent_time[end] = self.represent_time.get(end, 0) + 1

            self.end_related_relation_num[end] = self.end_related_relation_num.get(end, 0) + 1

        for term, num in self.mention_time.items():
            term_words = set(term.lower().split())
            term_word_num = len(term_words)
            for other_term, other_num in self.mention_time.items():
                if len(set(other_term.lower().split()) & term_words) == term_word_num:
                    self.sum_mention_time[term] = self.mention_time.get(other_term) + self.sum_mention_time.get(
                        term, 0)
        print("init cal finished!")

    def count_all_word(self, ):
        for item in self.terms:

            uncamel_str_list = self.code_pre.clean(item)
            self.uncamel_map[item] = uncamel_str_list
            for word in uncamel_str_list:
                self.all_words[word] = self.all_words.get(word, 0) + 1
        print("init count_all_word finished!")
        # print(self.uncamel_map)

    def two_hop_delete(self, threshold=2):
        need_remove = set()
        for start, r, end in self.relations:
            if start not in self.start_record_for_linkage and start not in self.end_record_for_linkage and end not in self.start_record_for_linkage and end not in self.end_record_for_linkage:
                need_remove.add(start)
                need_remove.add(end)
            else:
                if start in need_remove:
                    need_remove.remove(start)
                if end in need_remove:
                    need_remove.remove(end)
        need_remove = [(key, self.all_relation[key]) for key in need_remove]
        need_remove = sorted(need_remove, key=lambda x: x[1], reverse=True)
        move = [key for key, num in need_remove if num < threshold]
        return move

    def delete_based_on_name(self, sim_threshold=0.5, tf_threshold=3, mention_threshold=2):
        move_sim = []
        move_term = set()
        for term in self.terms:
            uncamel_name_list = self.uncamel_map.get(term,
                                                     self.uncamel_util.uncamelize_by_stemming(term).split(" "))
            sim = self.cal_sim(uncamel_name_list, self.all_words)
            move_sim.append((term, sim))
            if not uncamel_name_list:
                move_term.add(term)
        move_sim = sorted(move_sim, key=lambda x: x[1])
        move_sim = [item[0] for item in move_sim if item[1] < sim_threshold]

        for item in move_sim:
            if item not in self.end_record_for_linkage and item not in self.start_record_for_linkage:
                tf = self.all_relation.get(item, 0)
                if tf <= tf_threshold:
                    move_term.add(item)
            else:
                if item in self.represent_time or item in self.operation_time or item in self.instance_of_time:
                    continue
                if item in self.mention_time:
                    if self.mention_time[item] <= mention_threshold:
                        move_term.add(item)
        return list(move_term)

    def cal_sim(self, name_list, all_words):
        if not len(name_list):
            return 0
        same_count = 0
        for item in name_list:
            if item in all_words.keys():
                if all_words[item] > 1:
                    same_count += 1
        return float(same_count) / float(len(name_list))

    def delete_based_on_aliase_tf(self, sim_threshold=0.7):
        preprocess_doc_collection: PreprocessMultiFieldDocumentCollection = PreprocessMultiFieldDocumentCollection.load(
            self.pre_doc_collection_out_path)
        preprocess_multi_field_doc_list = preprocess_doc_collection.get_all_preprocess_document_list()
        corpus_clean_text = []
        for docno, multi_field_doc in enumerate(preprocess_multi_field_doc_list):
            corpus_clean_text.append(multi_field_doc.get_document_text_words())
        dict = Dictionary(corpus_clean_text)

        alise_tf_map = {}
        alise_score_map = {}
        for item in self.terms:
            current_alise = self.aliases_map.get(item, "")
            current_alise = [x.lower() for x in current_alise]
            current_alise = set(current_alise)
            current_alise.add(item.lower())
            code_pre_set = set()
            for alise in current_alise:
                code_pre_set.update(set(self.code_pre.clean(alise)))
            word_tf = []
            tf_sum = 0
            for word in code_pre_set:
                if word in dict.token2id:
                    tf_value = dict.cfs[dict.token2id[word]]
                    tf_sum += tf_value
                    word_tf.append((word, tf_value))
                else:
                    word_tf.append((word, 0))
            alise_tf_map[item] = word_tf
            if tf_sum == 0:
                alise_score_map[item] = 0
            else:
                alise_score_map[item] = float(tf_sum) / float(len(code_pre_set))
        move_item = [key for key in alise_tf_map if alise_score_map[key] < sim_threshold]
        return move_item

    def delete_based_on_name_length(self, length_threshold=30, number_threshold=3):
        move_item = []
        for item in self.terms:
            if len(item) > length_threshold and len(item.split(" ")) > number_threshold:
                move_item.append(item)
        return move_item

    def save(self, ):
        EntityReader.write_json_data(str(Path(domain_dir) / "start_record.json"), self.start_record_for_linkage)
        EntityReader.write_json_data(str(Path(domain_dir) / "start_record_relation.json"), self.start_with_r_record)
        EntityReader.write_line_data(str(Path(domain_dir) / "start_record_relation.txt"),
                                     [k + ":" + str(v) for k, v in self.start_with_r_record.items()])

        EntityReader.write_json_data(str(Path(domain_dir) / "end_record.json"), self.end_record_for_linkage)
        EntityReader.write_json_data(str(Path(domain_dir) / "end_record_relation.json"), self.end_with_r_record)
        EntityReader.write_line_data(str(Path(domain_dir) / "end_record_relation.txt"),
                                     [k + ":" + str(v) for k, v in self.end_with_r_record.items()])

        EntityReader.write_line_data(str(Path(domain_dir) / "mention_num.txt"),
                                     [str(v) + ":" + str(k) for k, v in self.mention_time.items()])
        EntityReader.write_line_data(str(Path(domain_dir) / "sum_mention_time.txt"),
                                     [str(v) + ":" + str(k) for k, v in self.sum_mention_time.items()])

        EntityReader.write_line_data(str(Path(domain_dir) / "end_related_relation_num.txt"),
                                     [str(v) + ":" + str(k) for k, v in self.end_related_relation_num.items()])


if __name__ == "__main__":
    domain_dir = PathUtil.domain_concept_dir("JabRef-2.6", version="v1")
    domain_dir = Path(domain_dir)
    term_save_path = str(domain_dir / "terms.txt")
    operation_save_path = str(domain_dir / "operations.txt")
    term_relation_save_path = str(domain_dir / "relations.json")
    linkage_save_path = str(domain_dir / "linkages.json")
    aliase_save_path = str(domain_dir / "aliases.json")

    pre_doc_collection_out_path = PathUtil.pre_doc(pro_name="JabRef-2.6", version="v2", pre_way="code-pre")

    reduce = ReduceDomainTerm(term_save_path, operation_save_path, term_relation_save_path, linkage_save_path,
                              aliase_save_path, pre_doc_collection_out_path)
    delete_based_on_name = reduce.delete_based_on_name()
    print(delete_based_on_name)
    print(len(delete_based_on_name))
    delete_based_on_aliase_tf = reduce.delete_based_on_aliase_tf()
    print(delete_based_on_aliase_tf)
    print(len(delete_based_on_aliase_tf))
    delete_based_on_name_length = reduce.delete_based_on_name_length()
    print(delete_based_on_name_length)
    print(len(delete_based_on_name_length))
