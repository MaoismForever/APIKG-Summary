import pickle
import traceback
from pathlib import Path

import gensim
import numpy as np
from gensim.models import KeyedVectors
from sekg.constant.constant import PropertyConstant, DomainConstant, WikiDataConstance
from sekg.graph.exporter.graph_data import GraphData
from sekg.ir.models.avg_w2v import AVGW2VFLModel
from sekg.ir.preprocessor.code_text import CodeDocPreprocessor, PureCodePreprocessor
from sekg.text.extractor.domain_entity.nlp_util import SpacyNLPFactory
from sekg.wiki.WikiDataItem import WikiDataItem
from sekg.wiki.search_domain_wiki.wikidata_searcher import AsyncWikiSearcher
from sekg.wiki.wiki_util import WikiDataPropertyTable
from spacy.lang.en import LEMMA_INDEX, LEMMA_EXC, LEMMA_RULES
from spacy.lemmatizer import Lemmatizer


class GenericKGFusion:
    INVALID_TEXTS = {"scientific article", "wikimedia template", "wikimedia list article", "wikipedia template",
                     "wikibase wikis", "wikimedia", "wikibase", "wikidata"}
    INVALID_SUBCLASS_ITEM_ID = set(["Q11424",  # film
                                    "Q15138389",  # wiki
                                    "Q7187",  # gene
                                    ])

    DEFAULT_FILTER_CONTEXT_SCORE = 0.8
    DEFAULT_FILTER_TOPIC_SCORE = 0.9

    DEFAULT_ACCEPTABLE_TOPIC_SCORE = 0.95
    DEFAULT_ACCEPTABLE_CONTEXT_SCORE = 0.85

    DEFAULT_PROXY_SERVER = "http://127.0.0.1:1080"

    def __init__(self, filter_score=DEFAULT_FILTER_CONTEXT_SCORE, proxy_server=DEFAULT_PROXY_SERVER):
        self.lemmatizer = Lemmatizer(LEMMA_INDEX, LEMMA_EXC, LEMMA_RULES)
        self.wikipedia_cache = {}
        self.fetcher = AsyncWikiSearcher(proxy_server)
        self.graph_data = GraphData()
        self.wikidata_property_table = WikiDataPropertyTable.get_instance()
        self.embedding = {}
        self.filter_score = filter_score
        self.NLP = SpacyNLPFactory.create_simple_nlp_pipeline()
        self.all_domain_vector = {}

    def init_wd_from_cache(self, title_save_path=None, item_save_path=None):
        self.fetcher.init_from_cache(title_save_path=title_save_path, item_save_path=item_save_path)
        print("Init from cache...")

    def init_wikipedia_contex(self, wikipedia_context_path=None):
        # TODO 将wikipedia的内容加到wikisearcher这个类里，就不用在GenericKGFusion中load了
        if wikipedia_context_path is not None and Path(wikipedia_context_path).exists():
            with open(wikipedia_context_path, "rb") as f:
                self.wikipedia_cache = pickle.load(f)
        else:
            print('no such wikipedia_context_path {}'.format(wikipedia_context_path))

    def export_wd_cache(self, title_save_path, item_save_path):
        self.fetcher.save(item_save_path=item_save_path, title_save_path=title_save_path)

    def load_word_embedding(self, emb_path):
        wv = KeyedVectors.load(emb_path)
        self.embedding = {k: wv[k] for k in wv.vocab.keys()}

    def load_w2v_model(self, w2v_path):
        self.w2v_model = AVGW2VFLModel.load(w2v_path)

    def init_graph_data(self, graph_data_path):
        self.graph_data = GraphData.load(graph_data_path)

    def fetch_wikidata_by_name(self, terms, title_save_path=None, item_save_path=None):
        """
                search with some terms and find the candidate wikidata item list for the term,
                 and cache all the possible wikidata item for the item.
                 eg. for term: "apple", we will search it in wikidata.org by API and get the returned
                 search result list(maybe 10 result). the search result for keywords will be cached.
                 And we we retrieve all 10 candidate wikidata item info.

                :param item_save_path: the wikidata item info cache path
                :param title_save_path:  the search result by title saving path
                :param terms: a list of str or a set of str standing for concepts.
                :return:
                """
        self.fetcher.init_from_cache(title_save_path=title_save_path, item_save_path=item_save_path)
        terms = {self.lemmatizer.noun(term)[0].lower() for term in terms}
        print("need to fetch %r term wiki titles, %r are already cache, actual %r need to fetch" % (
            len(terms), len(self.fetcher.title_cache.keys() & terms),
            len(terms) - len(self.fetcher.title_cache.keys() & terms)))

        term_titles = self.fetcher.search_title(terms)
        if title_save_path is not None:
            self.fetcher.save(title_save_path=title_save_path)

        ids = self.get_valid_wikidata_item(term_titles)
        term_wikiitems = self.fetch_wikidata_by_id(ids, item_save_path)
        return term_titles, term_wikiitems

    @staticmethod
    def is_need_to_fetch_wikidata_item(item):
        INVALID_TEXTS = ["scientific article", "wikimedia template", "wikimedia list article", "wikipedia template",
                         "wikibase wikis", "wikimedia"]

        snippet = item["snippet"].lower()
        for invalid_text in INVALID_TEXTS:
            if invalid_text in snippet:
                return False

        return True

    @staticmethod
    def get_valid_wikidata_item(term_titles):
        """
        some search results for wikidata are not need to search, for example, the item has "scientific article" in description.
        :param term_titles:
        :return:
        """
        valid_wikidata_ids = set([])

        for v in term_titles.values():
            for item in v:
                if GenericKGFusion.is_need_to_fetch_wikidata_item(item) == False:
                    continue
                valid_wikidata_ids.add(item["title"])

        return valid_wikidata_ids

    def fetch_wikidata_by_id(self, ids, item_save_path=None):

        print("need to fetch wikidata items num=%r, %r are already cache, actual %r need to fetch" % (
            len(ids), len(self.fetcher.item_cache.keys() & ids),
            len(ids) - len(self.fetcher.item_cache.keys() & ids)))

        term_wikiitems = self.fetcher.fetch_item(ids)
        if item_save_path is not None:
            self.fetcher.save(item_save_path=item_save_path)
        return term_wikiitems

    # def compute_topic_vector(self):
    #     topic_words = []
    #     for node_id in self.graph_data.get_node_ids_by_label(DomainConstant.LABEL_DOMAIN_TERM):
    #         try:
    #             node_json = self.graph_data.get_node_info_dict(node_id=node_id)
    #             if not node_json:
    #                 continue
    #             node_properties = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]
    #             lemma = node_properties[PropertyConstant.LEMMA]
    #             aliases = node_properties.get(PropertyConstant.ALIAS, [])
    #             aliases_en = node_properties.get("aliases_en", [])
    #             description_en = node_properties.get("descriptions_en", "")
    #             name = node_properties.get("name", "")
    #             topic_words.append(lemma)
    #             topic_words.extend(aliases)
    #             topic_words.extend(aliases_en)
    #             topic_words.append(description_en)
    #             topic_words.append(name)
    #         except:
    #             traceback.print_exc()
    #     topic_text = " ".join(topic_words).lower()
    #
    #     if len(topic_text) == 0:
    #         return None
    #     words = [w for w in topic_text.split() if w]
    #     if len(words) == 0:
    #         return None
    #     vec_des = sum([self.embedding.get(w, np.zeros([100])) for w in words]) / len(words)
    #
    #     return vec_des
    #
    # def compute_wikidata_vector(self, wikidata_item, term_wikiitems, node_json):
    #     relation_text = self.generate_relations_text(wikidata_item, term_wikiitems)
    #     description = wikidata_item.get_en_description()
    #     en_name = wikidata_item.get_en_name()
    #     en_aliases = wikidata_item.get_en_aliases()
    #
    #     description = " ".join([en_name, " ".join(en_aliases), description, relation_text])
    #
    #     words = [token.lemma_.lower() for token in self.NLP(description) if
    #              token.is_digit == False and token.is_stop == False and token.is_punct == False]
    #
    #     domain_term_name = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES][PropertyConstant.LEMMA]
    #
    #     removal_words = set(domain_term_name.lower().split())
    #     words = [w for w in words if w not in removal_words]
    #
    #     if len(words) == 0:
    #         return None
    #     # todo: the size of vector should be adjust
    #     vec_des = sum([self.embedding.get(w, np.zeros([100])) for w in words]) / len(words)
    #
    #     return vec_des
    #
    # def __score_topic(self, topic_vector, wikidata_item, term_wikiitems, node_json):
    #
    #     wikidata_vector = self.compute_wikidata_vector(wikidata_item, term_wikiitems, node_json)
    #     return self.compute_sim_for_two_vectors(wikidata_vector, topic_vector)
    #
    # def __score_context(self, node_json, wikidata_item, term_wikiitems):
    #     relation_text = self.generate_relations_text(wikidata_item, term_wikiitems)
    #     description = wikidata_item.get_en_description()
    #     en_name = wikidata_item.get_en_name()
    #     en_aliases = wikidata_item.get_en_aliases()
    #
    #     description = " ".join([en_name, " ".join(en_aliases), description, relation_text])
    #
    #     domain_term_name = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES][PropertyConstant.LEMMA]
    #
    #     name = self.get_compare_name_for_domain_term(node_json)
    #
    #     removal_words = set(domain_term_name.lower().split())
    #
    #     if len(description) == 0 or len(name) == 0:
    #         return 0
    #     # words = list(set(
    #     #     [token.lemma_.lower() for token in self.NLP(description) if
    #     #      token.is_digit == False and token.is_stop == False]))
    #     words = [token.lemma_.lower() for token in self.NLP(description) if
    #              token.is_digit == False and token.is_stop == False and token.is_punct == False]
    #     words = [w for w in words if w not in removal_words]
    #
    #     if len(words) == 0:
    #         return 0
    #     vec_des = sum([self.embedding.get(w, np.zeros([100])) for w in words]) / len(words)
    #     # name_words = list(
    #     #     set([token.lemma_.lower() for token in self.NLP(name) if
    #     #          token.is_digit == False and token.is_stop == False]))
    #     name_words = [token.lemma_.lower() for token in self.NLP(name) if
    #                   token.is_digit == False and token.is_stop == False]
    #
    #     if len(name_words) == 0:
    #         return 0
    #     vec_term = sum([self.embedding.get(w, np.zeros([100])) for w in name_words]) / len(name_words)
    #
    #     return self.compute_sim_for_two_vectors(vec_des, vec_term)
    #
    # def compute_sim_for_two_vectors(self, vec_des, vec_term):
    #     norm_des = np.linalg.norm(vec_des)
    #     norm_term = np.linalg.norm(vec_term)
    #     if norm_des == 0 or norm_term == 0:
    #         return 0
    #     return 0.5 + vec_des.dot(vec_term) / (norm_des * norm_term) / 2
    #
    # def get_compare_name_for_domain_term(self, node_json):
    #     domain_term_id = node_json[GraphData.DEFAULT_KEY_NODE_ID]
    #
    #     name = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES].get(PropertyConstant.LEMMA, "")
    #     aliases = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES].get(PropertyConstant.ALIAS, [])
    #     aliases_en = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES].get("aliases_en", [])
    #
    #     other_names = [name]
    #     other_names.extend(aliases)
    #     other_names.extend(aliases_en)
    #
    #     out_relations = self.graph_data.get_all_out_relations(node_id=domain_term_id)
    #     in_relations = self.graph_data.get_all_in_relations(node_id=domain_term_id)
    #     domain_term_node_ids = self.graph_data.label_to_ids_map[DomainConstant.LABEL_DOMAIN_TERM]
    #     id_set = set([])
    #     for (start_id, r, end_id) in out_relations:
    #         if end_id in domain_term_node_ids:
    #             id_set.add(end_id)
    #     for (start_id, r, end_id) in in_relations:
    #         if start_id in domain_term_node_ids:
    #             id_set.add(start_id)
    #     id_set.add(domain_term_id)
    #     for id in id_set:
    #         temp_node_json = self.graph_data.get_node_info_dict(node_id=id)
    #         other_names.append(temp_node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES].get(PropertyConstant.LEMMA, ""))
    #     name = " ".join(other_names)
    #     return name

    def add_wikidata_item(self, item: WikiDataItem):
        """
        在图中添加一个wikidata的节点，没有添加relation
        add a new term to graph data
        :param term: the term added to GraphData
        :return: the node_id fo the added term node
        """
        ori_node_json = self.graph_data.find_one_node_by_property(WikiDataConstance.PRIMARY_PROPERTY_NAME,
                                                                  item.wd_item_id)
        if ori_node_json:
            # print(ori_node_json)
            # print('no new wiki node!! node %d has fused wiki_node %s' % (ori_node_json["id"], item.wd_item_id))
            return ori_node_json["id"]
        # print("add new wikinode %s" % (item.wd_item_id))
        node_labels = [WikiDataConstance.LABEL_WIKIDATA]
        node_properties = {
            WikiDataConstance.PRIMARY_PROPERTY_NAME: item.wd_item_id,
            WikiDataConstance.NAME: item.get_en_name(),
            PropertyConstant.ALIAS: set(item.get_en_aliases()),
        }
        item.get_relation_property_name_list()
        relation_property_set = set(item.relation_property_name_list)
        pure_property_set = set(item.get_non_relation_property_name_list())

        valid_property_dict = {}
        for p, v in item.data_dict.items():
            if p in relation_property_set:
                continue
            if p in pure_property_set:
                p = self.wikidata_property_table.property_id_2_name(p)
                if p == None:
                    continue
            valid_property_dict[p] = v
        wikidata_node_id = self.graph_data.add_node(node_labels=node_labels,
                                                    node_properties=dict(valid_property_dict, **node_properties),
                                                    primary_property_name=WikiDataConstance.PRIMARY_PROPERTY_NAME)
        return wikidata_node_id

    def add_all_wiki_nodes(self):
        print("start add all wiki nodes.......")
        term_wikiitems = self.fetcher.item_cache
        wikiiterms_ids = term_wikiitems.keys()
        self.add_wikidata_items(wikiiterms_ids)
        self.graph_data.refresh_indexer()

    def simple_fuse(self, ):
        """
        simple fuse wiki data, the graph is with all wikidata nodes, we need to calculate similarity to filter some
        :return:
        """
        record = []
        valid_domain_id_set = self.graph_data.get_node_ids_by_label(DomainConstant.LABEL_DOMAIN_TERM)
        i = 0
        valid_wiki_id_set = self.graph_data.get_node_ids_by_label(WikiDataConstance.LABEL_WIKIDATA)
        valid_wiki_index = np.array(list(self.w2v_model.preprocess_doc_collection.doc_id_set_2_doc_index_set(
            valid_wiki_id_set)))
        doc_model = self.w2v_model.avg_w2v_model_field_map["doc"]
        print("valid_doc_index size: ", valid_wiki_index.size)

        for node_id in valid_domain_id_set:
            try:
                node_json = self.graph_data.get_node_info_dict(node_id=node_id)
                if not node_json:
                    continue
                node_properties = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]
                lemma = node_properties[PropertyConstant.LEMMA]
                alias_set = node_properties[PropertyConstant.ALIAS]
                term_name = node_properties["term_name"]
                alias_set.add(lemma)
                alias_set.add(term_name)
                text = " ".join(list(alias_set))
                domain_words = self.w2v_model.preprocessor.clean(text)
                domain_vec = self.w2v_model.get_avg_w2v_vec(domain_words)
                score_vector = (doc_model.similar_by_vector(domain_vec, topn=None) + 1) / 2
                over_thred = np.where(score_vector > 0.8)
                top_wiki_valid = np.intersect1d(over_thred, valid_wiki_index)
                if top_wiki_valid.size:
                    print("number {}:{} ,Done!".format(i, node_id))
                score_vector = score_vector[top_wiki_valid]
                sort_index = np.argsort(-score_vector)
                score_vector = score_vector[sort_index]
                sorted_index_scores = np.array((sort_index, score_vector)).T
                retrieval_results = []
                rank = 0
                for (doc_index, score) in sorted_index_scores:
                    entity_document = self.w2v_model.doc_index2doc(doc_index)
                    if rank >= 5:
                        break
                    if entity_document is None:
                        continue
                    wiki_id = entity_document.get_document_id()
                    rank += 1
                    retrieval_results.append((wiki_id, score))

                for wiki_id, score in retrieval_results:
                    wiki_node_json = self.graph_data.get_node_info_dict(wiki_id)
                    record.append({
                        "name": wiki_node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]["wikidata_name"],
                        "alias": wiki_node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]["alias_en"],
                        "description": wiki_node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]["description_en"],
                        "domain term": node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]["qualified_name"],
                        "score": score,
                        "link": True,
                        "domain_id": node_id,
                        "wd_item_id": wiki_node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]["wd_item_id"]
                    })
                    self.graph_data.add_relation(startId=node_id, endId=wiki_id,
                                                 relationType="related to")
            except Exception:
                traceback.print_exc()
        self.delete_isolated_nodes_by_label(WikiDataConstance.LABEL_WIKIDATA)
        self.graph_data.refresh_indexer()
        return record

    @staticmethod
    def get_wikidata_item_ids_by_relation(wikidata_item: WikiDataItem, r):
        id_set = set([])
        end = wikidata_item.data_dict.get(r, [])
        if type(end) == list:
            for e in end:
                id_set.add(e)
        else:
            id_set.add(end)
        return id_set

    def generate_relations_text(self, wikidata_item, term_wikiitems):
        text = []
        for r in wikidata_item.relation_property_name_list:

            relation_name = self.wikidata_property_table.property_id_2_name(r)
            if relation_name == None:
                relation_name = r
            end = wikidata_item.data_dict[r]

            if type(end) == list:
                for e_wd_item_id in end:
                    if self.is_valid_wikidata_item_id(e_wd_item_id):
                        neibour_item = term_wikiitems.get(e_wd_item_id, None)
                        if neibour_item != None:
                            text.append(neibour_item.get_en_name())
                            # if relation_name in {"subclass of", "instance of", "part of"}:
                            #     text.append(neibour_item.get_en_description())
                            text.append(neibour_item.get_en_description())

                    else:
                        text.append(end)
                text.append(relation_name)

            else:
                if self.is_valid_wikidata_item_id(end):
                    neibour_item = term_wikiitems.get(end, None)
                    if neibour_item != None:
                        text.append(neibour_item.get_en_name())
                        # if relation_name in {"subclass of", "instance of", "part of"}:
                        #     text.append(neibour_item.get_en_description())
                        text.append(neibour_item.get_en_description())
                else:
                    text.append(end)
                text.append(relation_name)

        return " ".join(text)

    def is_valid_wikidata_item_id(self, wd_item_id):
        try:

            if wd_item_id.startswith("Q") and wd_item_id[1:].isdigit():
                return True
            return False
        except:
            return False

    def get_all_neighbours_id(self, item):
        neighbours = set()
        for r in item.relation_property_name_list:
            end = item.data_dict[r]
            if type(end) == list:
                for e in end:
                    if e[0] == "Q" or e[0] == "P":
                        neighbours.add(e)
            else:
                if end[0] == "Q" or end[0] == "P":
                    neighbours.add(end)

        return neighbours

    def get_all_neighbours_id_by_item_id(self, item_id):
        neighbours = set()
        item = self.fetcher.item_cache.get(item_id, None)
        if item == None:
            return set()
        neighbours = self.get_all_neighbours_id(item)
        return neighbours

    def fetch_valid_wikidata_item_neibours_from_all_term_titles(self, item_save_path):
        """
        some search results for wikidata are not need to search, for example, the item has "scientific article" in description.
        :param term_titles:
        :return:
        """
        term_titles = self.fetcher.title_cache
        valid_wikidata_ids = GenericKGFusion.get_valid_wikidata_item(term_titles)
        nerbours = set([])

        for valid_id in valid_wikidata_ids:
            nerbours.update(self.get_all_neighbours_id_by_item_id(valid_id))
        return self.fetch_wikidata_by_id(nerbours, item_save_path)

    def add_wikidata_items(self, wd_item_ids):
        term_wikiitems = self.fetcher.item_cache
        self.graph_data.refresh_indexer()
        i = 0
        for wd_item_id in wd_item_ids:
            i += 1
            self.add_wikidata_item(term_wikiitems[wd_item_id])
            if i == 50:
                break
        self.build_relation_between_wikidata_node_in_graph(term_wikiitems)

    def build_relation_between_wikidata_node_in_graph(self, term_wikiitems):
        wikidata_node_ids = self.graph_data.get_node_ids_by_label(WikiDataConstance.LABEL_WIKIDATA)
        wd_item_id_2_node_id_map = {}
        node_id_2_wd_item_id_map = {}
        for node_id in wikidata_node_ids:
            wikidata_node = self.graph_data.get_node_info_dict(node_id)
            wd_item_id = wikidata_node[GraphData.DEFAULT_KEY_NODE_PROPERTIES][WikiDataConstance.PRIMARY_PROPERTY_NAME]
            wd_item_id_2_node_id_map[wd_item_id] = node_id
            node_id_2_wd_item_id_map[node_id] = wd_item_id
        for start_wd_item_id, start_node_id in wd_item_id_2_node_id_map.items():
            start_wikidata_item = term_wikiitems.get(start_wd_item_id, None)
            if start_wikidata_item == None:
                continue
            for r_id in start_wikidata_item.relation_property_name_list:
                end_wd_ids = self.get_wikidata_item_ids_by_relation(start_wikidata_item, r_id)
                relation_name = self.wikidata_property_table.property_id_2_name(r_id)
                if relation_name == None:
                    continue

                for end_wd_id in end_wd_ids:
                    end_node_id = wd_item_id_2_node_id_map.get(end_wd_id, None)
                    if end_node_id == None:
                        continue
                    if start_node_id == end_node_id:
                        continue
                    self.graph_data.add_relation(start_node_id, relation_name, end_node_id)

    def save(self, graph_data_path):
        self.graph_data.save(graph_data_path)
        print("save ", type(self.graph_data))

    def is_valid_wikidata_item(self, item):
        for text in self.INVALID_TEXTS:
            en_name = item.get_en_name().lower()
            if text in en_name:
                return False

        end_wd_ids = self.get_wikidata_item_ids_by_relation(item, "P31")

        for end_wd in end_wd_ids:
            if end_wd in self.INVALID_SUBCLASS_ITEM_ID:
                return False

        return True

    def fetch_wikidata_by_name_and_cache_neibours(self, terms, title_save_path, item_save_path):
        self.fetch_wikidata_by_name(terms, item_save_path=item_save_path, title_save_path=title_save_path)
        self.fetch_valid_wikidata_item_neibours_from_all_term_titles(item_save_path=item_save_path)

    def delete_isolated_nodes_by_label(self, label):
        label_ids = self.graph_data.get_node_ids_by_label(label)
        remove_id = set()
        for id in label_ids:
            in_relations = self.graph_data.get_all_in_relations(id)
            out_relations = self.graph_data.get_all_out_relations(id)
            if not in_relations and not out_relations:
                remove_id.add(id)
                print("remove {}: {}".format(label, id))
        for id in remove_id:
            self.graph_data.remove_node(id)
        print("remove {} wiki nodes".format(len(remove_id)))
