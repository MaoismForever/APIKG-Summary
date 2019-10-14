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
        print("#############", type(self.graph_data))

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

    def compute_topic_vector(self):
        topic_words = []
        for node_id in self.graph_data.get_node_ids_by_label(DomainConstant.LABEL_DOMAIN_TERM):
            try:
                node_json = self.graph_data.get_node_info_dict(node_id=node_id)
                if not node_json:
                    continue
                node_properties = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]
                lemma = node_properties[PropertyConstant.LEMMA]
                aliases = node_properties.get(PropertyConstant.ALIAS, [])
                aliases_en = node_properties.get("aliases_en", [])
                description_en = node_properties.get("descriptions_en", "")
                name = node_properties.get("name", "")
                topic_words.append(lemma)
                topic_words.extend(aliases)
                topic_words.extend(aliases_en)
                topic_words.append(description_en)
                topic_words.append(name)
            except:
                traceback.print_exc()
        topic_text = " ".join(topic_words).lower()

        if len(topic_text) == 0:
            return None
        words = [w for w in topic_text.split() if w]
        if len(words) == 0:
            return None
        vec_des = sum([self.embedding.get(w, np.zeros([100])) for w in words]) / len(words)

        return vec_des

    def compute_wikidata_vector(self, wikidata_item, term_wikiitems, node_json):
        relation_text = self.generate_relations_text(wikidata_item, term_wikiitems)
        description = wikidata_item.get_en_description()
        en_name = wikidata_item.get_en_name()
        en_aliases = wikidata_item.get_en_aliases()

        description = " ".join([en_name, " ".join(en_aliases), description, relation_text])

        # words = list(set(
        #     [token.lemma_.lower() for token in self.NLP(description) if
        #      token.is_digit == False and token.is_stop == False]))
        words = [token.lemma_.lower() for token in self.NLP(description) if
                 token.is_digit == False and token.is_stop == False and token.is_punct == False]

        domain_term_name = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES][PropertyConstant.LEMMA]

        removal_words = set(domain_term_name.lower().split())
        words = [w for w in words if w not in removal_words]

        if len(words) == 0:
            return None
        # todo: the size of vector should be adjust
        vec_des = sum([self.embedding.get(w, np.zeros([100])) for w in words]) / len(words)

        return vec_des

    def __score_topic(self, topic_vector, wikidata_item, term_wikiitems, node_json):

        wikidata_vector = self.compute_wikidata_vector(wikidata_item, term_wikiitems, node_json)
        return self.compute_sim_for_two_vectors(wikidata_vector, topic_vector)

    def __score_context(self, node_json, wikidata_item, term_wikiitems):
        relation_text = self.generate_relations_text(wikidata_item, term_wikiitems)
        description = wikidata_item.get_en_description()
        en_name = wikidata_item.get_en_name()
        en_aliases = wikidata_item.get_en_aliases()

        description = " ".join([en_name, " ".join(en_aliases), description, relation_text])

        domain_term_name = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES][PropertyConstant.LEMMA]

        name = self.get_compare_name_for_domain_term(node_json)

        removal_words = set(domain_term_name.lower().split())

        if len(description) == 0 or len(name) == 0:
            return 0
        # words = list(set(
        #     [token.lemma_.lower() for token in self.NLP(description) if
        #      token.is_digit == False and token.is_stop == False]))
        words = [token.lemma_.lower() for token in self.NLP(description) if
                 token.is_digit == False and token.is_stop == False and token.is_punct == False]
        words = [w for w in words if w not in removal_words]

        if len(words) == 0:
            return 0
        vec_des = sum([self.embedding.get(w, np.zeros([100])) for w in words]) / len(words)
        # name_words = list(
        #     set([token.lemma_.lower() for token in self.NLP(name) if
        #          token.is_digit == False and token.is_stop == False]))
        name_words = [token.lemma_.lower() for token in self.NLP(name) if
                      token.is_digit == False and token.is_stop == False]

        if len(name_words) == 0:
            return 0
        vec_term = sum([self.embedding.get(w, np.zeros([100])) for w in name_words]) / len(name_words)

        return self.compute_sim_for_two_vectors(vec_des, vec_term)

    def compute_sim_for_two_vectors(self, vec_des, vec_term):
        norm_des = np.linalg.norm(vec_des)
        norm_term = np.linalg.norm(vec_term)
        if norm_des == 0 or norm_term == 0:
            return 0
        return 0.5 + vec_des.dot(vec_term) / (norm_des * norm_term) / 2

    def get_compare_name_for_domain_term(self, node_json):
        domain_term_id = node_json[GraphData.DEFAULT_KEY_NODE_ID]

        name = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES].get(PropertyConstant.LEMMA, "")
        aliases = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES].get(PropertyConstant.ALIAS, [])
        aliases_en = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES].get("aliases_en", [])

        other_names = [name]
        other_names.extend(aliases)
        other_names.extend(aliases_en)

        out_relations = self.graph_data.get_all_out_relations(node_id=domain_term_id)
        in_relations = self.graph_data.get_all_in_relations(node_id=domain_term_id)
        domain_term_node_ids = self.graph_data.label_to_ids_map[DomainConstant.LABEL_DOMAIN_TERM]
        id_set = set([])
        for (start_id, r, end_id) in out_relations:
            if end_id in domain_term_node_ids:
                id_set.add(end_id)
        for (start_id, r, end_id) in in_relations:
            if start_id in domain_term_node_ids:
                id_set.add(start_id)
        id_set.add(domain_term_id)
        for id in id_set:
            temp_node_json = self.graph_data.get_node_info_dict(node_id=id)
            other_names.append(temp_node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES].get(PropertyConstant.LEMMA, ""))
        name = " ".join(other_names)
        return name

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

    def fuse_wikidata_item(self, domain_id, item: WikiDataItem):
        """
        将wikidataitem的内容融合到domain item的节点中
        add WikiDataItem into to domian term node
        :domain_id: domain_term id
        :param term: the term added to GraphData
        :return: the node_id fo the added term node
        """
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

        self.graph_data.add_labels(WikiDataConstance.LABEL_WIKIDATA)
        self.graph_data.add_label_by_node_id(domain_id, WikiDataConstance.LABEL_WIKIDATA)
        domain_node_json = self.graph_data.get_node_info_dict(domain_id)
        domain_properties_json = domain_node_json[self.graph_data.DEFAULT_KEY_NODE_PROPERTIES]
        if domain_node_json:
            for k, v in dict(valid_property_dict, **node_properties).items():
                if k in domain_properties_json:
                    if v == domain_properties_json[k]:
                        pass
                    else:
                        if type(v) == set:
                            domain_properties_json[k] = domain_properties_json[k].union(v)
                        if type(v) == list:
                            domain_properties_json[k].extend(v)
                        if type(v) == str:
                            domain_properties_json[k + "_wiki"] = v
                else:
                    domain_properties_json[k] = v
        # print("fuse node %d and wiki node %s" % (domain_id, item.wd_item_id))
        # print("&" * 10)
        # print(self.graph_data.get_node_info_dict(domain_id))
        return domain_id

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
        term_wikiitems = self.fetcher.item_cache
        term_wikipedia = self.wikipedia_cache
        i = 0
        valid_doc_index = np.array(list(self.w2v_model.preprocess_doc_collection.doc_id_set_2_doc_index_set(
            valid_domain_id_set)))
        doc_model = self.w2v_model.avg_w2v_model_field_map["doc"]
        print("valid_doc_index size: ", valid_doc_index.size)
        for key, wikiitem in term_wikiitems.items():
            i += 1
            try:
                wiki_text = ""
                wikipedia_context = term_wikipedia.get(key, [])
                if wikipedia_context:
                    wiki_text = " ".join([context["context"] for context in wikipedia_context])
                if not wiki_text:
                    relation_text = self.generate_relations_text(wikiitem, term_wikiitems)
                    description = wikiitem.get_en_description()
                    en_name = wikiitem.get_en_name()
                    en_aliases = wikiitem.get_en_aliases()
                    wiki_text = " ".join([en_name, " ".join(en_aliases), relation_text, description])
                wiki_words = self.w2v_model.preprocessor.clean(wiki_text)
                wiki_vec = self.w2v_model.get_avg_w2v_vec(wiki_words)
                score_vector = (doc_model.similar_by_vector(wiki_vec, topn=None) + 1) / 2
                over_thred = np.where(score_vector > 0.8)
                top_domain_valid = np.intersect1d(over_thred, valid_doc_index)
                if top_domain_valid.size:
                    print("number {}:{} ,Done!".format(i, key))
                score_vector = score_vector[top_domain_valid]
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
                    document_id = entity_document.get_document_id()
                    rank += 1
                    retrieval_results.append((document_id, score))
                for id, score in retrieval_results:
                    domain_node_json = self.graph_data.get_node_info_dict(id)
                    record.append({
                        "name": wikiitem.get_en_name(),
                        "alias": wikiitem.get_en_aliases(),
                        "description": wikiitem.get_en_description(),
                        "wk relation text": self.generate_relations_text(wikiitem, term_wikiitems),
                        "domain term": domain_node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]["qualified_name"],
                        "score": score,
                        "combined name": self.get_compare_name_for_domain_term(domain_node_json),
                        "link": True,
                        "domain_id": id,
                        "wd_item_id": wikiitem.wd_item_id
                    })
                    wikidata_node_id = self.add_wikidata_item(wikiitem)
                    self.graph_data.add_relation(startId=id, endId=wikidata_node_id,
                                                 relationType="related to")
            except Exception:
                traceback.print_exc()
        self.delete_isolated_nodes_by_label(WikiDataConstance.LABEL_WIKIDATA)
        self.graph_data.refresh_indexer()
        return record

    def fuse(self, ):
        self.graph_data.create_index_on_property(WikiDataConstance.PRIMARY_PROPERTY_NAME)
        term_titles = self.fetcher.title_cache
        # todo: by calling the method not access the field
        term_wikiitems = self.fetcher.item_cache

        id_item = {}
        record = []
        topic_vector = self.compute_topic_vector()
        if topic_vector is None:
            print("error, topic vector is None, maybe the graph has not domain term")
            return
        for node_id in self.graph_data.get_node_ids_by_label(DomainConstant.LABEL_DOMAIN_TERM):
            try:
                node_json = self.graph_data.get_node_info_dict(node_id=node_id)
                # print("#" * 10)
                # print(node_json)
                if not node_json:
                    continue
                if WikiDataConstance.LABEL_WIKIDATA not in node_json["labels"]:
                    node_properties = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]
                    lemma = node_properties[PropertyConstant.LEMMA]
                    alias_set = node_properties[PropertyConstant.ALIAS]
                    alias_set.add(lemma)
                    items = set()
                    for lemma in alias_set:
                        if lemma in term_titles:
                            titles = term_titles[lemma]
                            for title in titles:
                                item = term_wikiitems.get(title["title"], None)
                                if item is None or lemma not in {alias.lower() for alias in
                                                                 item.get_en_aliases()}:
                                    continue
                                if self.is_valid_wikidata_item(item) == False:
                                    continue
                                items.add(item)

                    if len(items) == 0:
                        continue
                    items = list(items)
                    # sims = [(item, self.__score_context(node_json, item, term_wikiitems)) for item in items]
                    # topic_sims = [(item, self.__score_topic(topic_vector, item, term_wikiitems)) for item in items]
                    sims = [(item, self.__score_context(node_json, item, term_wikiitems),
                             self.__score_topic(topic_vector, item, term_wikiitems, node_json)) for item in items]
                    best_link_wikidata_item = None
                    best_context_score = 0
                    best_topic_score = 0

                    item_max_by_context, context_score, topic_score = max(sims, key=lambda x: x[1])

                    if context_score > self.DEFAULT_ACCEPTABLE_CONTEXT_SCORE:
                        best_link_wikidata_item = item_max_by_context
                        best_context_score = context_score
                        best_topic_score = topic_score

                    item_max_by_topic, context_score, topic_score = max(sims, key=lambda x: x[2])

                    sims = sorted(sims, key=lambda x: x[1], reverse=True)

                    if topic_score > self.DEFAULT_ACCEPTABLE_TOPIC_SCORE:
                        best_link_wikidata_item = item_max_by_topic
                        best_context_score = context_score
                        best_topic_score = topic_score

                    if best_link_wikidata_item == None:
                        for item, context_score, topic_score in sims:
                            if context_score > self.DEFAULT_FILTER_CONTEXT_SCORE and topic_score > self.DEFAULT_FILTER_TOPIC_SCORE:
                                best_link_wikidata_item = item
                                best_context_score = context_score
                                best_topic_score = topic_score
                                break

                    is_link = True
                    if best_link_wikidata_item is None:
                        best_link_wikidata_item, best_context_score, best_topic_score = sims[0]
                        is_link = False

                    record.append({
                        "name": best_link_wikidata_item.get_en_name(),
                        "alias": best_link_wikidata_item.get_en_aliases(),
                        "description": best_link_wikidata_item.get_en_description(),
                        "wk relation text": self.generate_relations_text(best_link_wikidata_item, term_wikiitems),
                        "domain term": lemma,
                        "score": best_context_score + best_topic_score,
                        "context_score": best_context_score,
                        "topic_score": best_topic_score,
                        "combined name": self.get_compare_name_for_domain_term(node_json),
                        "link": is_link,
                        "domain_id": node_id,
                        "wd_item_id": best_link_wikidata_item.wd_item_id
                    })

                    if best_link_wikidata_item == None:
                        continue

                    # wikidata_node_id = self.add_wikidata_item(best_link_wikidata_item)
                    if is_link:
                        wikidata_node_id = self.fuse_wikidata_item(node_id, best_link_wikidata_item)
                        if wikidata_node_id == GraphData.UNASSIGNED_NODE_ID:
                            continue
                        id_item[wikidata_node_id] = best_link_wikidata_item
            except Exception:
                traceback.print_exc()
        self.build_relation_between_wikidata_node_in_graph(term_wikiitems)
        neighbours = set()
        for _id, item in id_item.items():
            for r in item.relation_property_name_list:
                end_id_set = self.get_wikidata_item_ids_by_relation(item, r)
                for e in end_id_set:
                    neighbours.add(e)
        self.graph_data.refresh_indexer()
        return neighbours, record

    def fuse_with_prefix_and_suffix(self):
        domain_ids = self.graph_data.get_node_ids_by_label(DomainConstant.LABEL_DOMAIN_TERM)
        wiki_ids = self.graph_data.get_node_ids_by_label("wikidata")
        unfuse_domain = domain_ids - wiki_ids
        unfuse_wiki = wiki_ids - domain_ids
        relations_set = set()
        domain_wiki_map = {}
        relations = []
        domain_wiki_fuse = []
        code_pre = CodeDocPreprocessor()
        clean_wiki_name_map = {}

        for wiki_id in unfuse_wiki:
            wiki_node_info = self.graph_data.get_node_info_dict(wiki_id)
            id = wiki_node_info["id"]
            wikidata_name = wiki_node_info[GraphData.DEFAULT_KEY_NODE_PROPERTIES]["wikidata_name"]
            aliases = wiki_node_info[GraphData.DEFAULT_KEY_NODE_PROPERTIES]["alias"]
            clean_wiki_name_map[id] = set()
            clean_wikidata_name = " ".join([code_pre.lemma(word) for word in wikidata_name.lower().split(" ")])
            if len(clean_wikidata_name) > 2:
                clean_wiki_name_map[id].add((wikidata_name, clean_wikidata_name))
            for ali in aliases:
                clean_wiki_alise = " ".join([code_pre.lemma(word) for word in ali.lower().split(" ")])
                if len(clean_wiki_alise) > 2:
                    clean_wiki_name_map[id].add((ali, clean_wiki_alise))
            if not clean_wiki_name_map[id]:
                clean_wiki_name_map.pop(id)

        for id in unfuse_domain:
            domain_node_info = self.graph_data.get_node_info_dict(id)
            domain_name = domain_node_info[self.graph_data.DEFAULT_KEY_NODE_PROPERTIES][
                DomainConstant.PRIMARY_PROPERTY_NAME]
            domain_name_list = domain_name.lower().split(" ")
            domain_name = " ".join([code_pre.lemma(word) for word in domain_name_list])

            for key in clean_wiki_name_map:
                for wiki_name, clean_wiki_name in clean_wiki_name_map[key]:
                    if domain_name == clean_wiki_name:
                        if id not in domain_wiki_map:
                            domain_wiki_map[id] = []
                            domain_wiki_map[id].append(key)
                        else:
                            domain_wiki_map[id].append(key)
                        domain_wiki_fuse.append(
                            {"domain_id": id, "domain_name": domain_name, "wiki_id": key, "wiki_name": wiki_name})
                        continue
                    if len(domain_name_list) > 1:
                        if domain_name.startswith(clean_wiki_name):
                            relations_set.add((id, "part of", key))
                            relations.append(
                                {"domain_id": id, "domain_name": domain_name, "relation": "part of", "wiki_id": key,
                                 "wiki_name": wiki_name})
                        if domain_name.endswith(clean_wiki_name):
                            relations_set.add((id, "is a", key))
                            relations.append(
                                {"domain_id": id, "domain_name": domain_name, "relation": "is a", "wiki_id": key,
                                 "wiki_name": wiki_name})
        # fuse wiki_node and domain_node , they have the same name
        remove_wiki_id_set = set()
        for domain_id in domain_wiki_map:
            wiki_id = domain_wiki_map[domain_id][0]
            remove_wiki_id_set.add(wiki_id)
            wiki_node = self.graph_data.get_node_info_dict(wiki_id)
            wd_item_id = wiki_node[GraphData.DEFAULT_KEY_NODE_PROPERTIES]["wd_item_id"]
            self.fuse_wikidata_item(domain_id, self.fetcher.item_cache[wd_item_id])
            wiki_in_relations = self.graph_data.get_all_in_relations(wiki_id)
            wiki_out_relations = self.graph_data.get_all_out_relations(wiki_id)
            for s, r, e in wiki_in_relations:
                self.graph_data.add_relation(s, r, domain_id)
            for s, r, e in wiki_out_relations:
                self.graph_data.add_relation(domain_id, r, e)
        print("fuse wiki_node and domain_node  %d" % (len(remove_wiki_id_set)))
        for wiki_id in remove_wiki_id_set:
            wiki_node = self.graph_data.get_node_info_dict(wiki_id)
            if DomainConstant.LABEL_DOMAIN_TERM not in wiki_node["labels"]:
                wiki_in_relations = self.graph_data.get_all_in_relations(wiki_id)
                wiki_out_relations = self.graph_data.get_all_out_relations(wiki_id)
                for s, r, e in wiki_in_relations:
                    self.graph_data.remove_relation(s, r, e)
                for s, r, e in wiki_out_relations:
                    self.graph_data.remove_relation(s, r, e)
                self.graph_data.remove_node(wiki_id)

        print("and new domian_wiki relation %d" % (len(relations_set)))
        for item in relations_set:
            s = item[0]
            r = item[1]
            e = item[2]
            self.graph_data.add_relation(s, r, e)
        return domain_wiki_fuse, relations

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

    def merge_domain_nodes_fuse_same_wiki_item(self, nodes):
        for i in range(1, len(nodes)):
            print("merge %d && %d !" % (nodes[0], nodes[i]))
            self.graph_data.merge_two_nodes_by_id(nodes[0], nodes[i], PropertyConstant.ALIAS, PropertyConstant.ALIAS)
            # print(self.graph_data.get_node_info_dict(nodes[0]))

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

    def delete_given_wiki_node(self):
        term_titles = self.fetcher.item_cache
        for wiki_id, item in term_titles.items():
            ori_node_json = self.graph_data.find_one_node_by_property(WikiDataConstance.PRIMARY_PROPERTY_NAME,
                                                                      item.wd_item_id)
            if ori_node_json:
                id = ori_node_json["id"]
                self.graph_data.remove_node(id)
                print("delete {} , {}".format(wiki_id, id))
        self.delete_isolated_nodes_by_label(WikiDataConstance.LABEL_WIKIDATA)
