import traceback
from pathlib import Path
from bs4 import BeautifulSoup
from sekg.graph.exporter.graph_data import GraphDataReader, GraphData
from sekg.ir.doc.wrapper import MultiFieldDocumentCollection, MultiFieldDocument

from doc.node_info import ProjectKGNodeInfoFactory, CodeElementNodeInfo, DomainEntityNodeInfo, OperationEntityNodeInfo, \
    WikidataEntityNodeInfo


## todo: fix this class, it should all be static method.
class GraphNodeDocumentBuilder:
    """
    build the basic Node Document from a exist NodeDocument
    """

    def __init__(self, graph_data):
        if isinstance(graph_data, GraphData):
            self.graph_data = graph_data
        elif isinstance(graph_data, Path):
            self.graph_data = GraphData.load(str(graph_data))
        elif isinstance(graph_data, str):
            self.graph_data = GraphData.load(graph_data)
        else:
            self.graph_data = None

        self.graph_data_reader = GraphDataReader(graph_data=self.graph_data,
                                                 node_info_factory=ProjectKGNodeInfoFactory())

        self.doc_collection = MultiFieldDocumentCollection()

    def init(self, doc_collection):
        """
        init from a exist doc collection
        :param doc_collection: could be a str pointing the path to MultiFieldDocumentCollection. or A exist MultiFieldDocumentCollection obj.
        :return:
        """
        if doc_collection is None:
            raise Exception("init from None")
        if isinstance(doc_collection, MultiFieldDocumentCollection):
            self.doc_collection = doc_collection
        elif isinstance(doc_collection, Path):
            self.doc_collection = MultiFieldDocumentCollection.load(str(doc_collection))
        elif isinstance(doc_collection, str):
            self.doc_collection = MultiFieldDocumentCollection.load(doc_collection)
        else:
            self.doc_collection = None

        print("init complete")

    def save(self, output_path):
        self.doc_collection.save(output_path)

    def build_doc_for_code_element(self, node_info: CodeElementNodeInfo):
        all_texts = []
        properties = ["short_description", "string_literal_expr", "comment", "declare", "inside_comment"]
        for property_name in properties:
            if property_name not in node_info.properties:
                continue
            property_value = node_info.properties[property_name]
            if property_name in ["comment", "declare"]:
                str_added = None
                if type(property_value) == str:
                    str_added = self.clean_comment(property_value)
                if type(property_value) == list:
                    for value in property_value:
                        str_added += self.clean_comment(value)
                self.doc_collection.add_field_to_doc(doc_id=node_info.node_id, field_name=property_name,
                                                     value=str_added)
            if type(property_value) == str:
                all_texts.append(self.clean_comment(property_value))
                continue
            if type(property_value) == list:
                for value in property_value:
                    all_texts.append(self.clean_comment(value))

        self.doc_collection.add_field_to_doc(doc_id=node_info.node_id, field_name="description",
                                             value=" . \n".join(all_texts))

        self.doc_collection.add_field_to_doc(doc_id=node_info.node_id, field_name="aliases",
                                             value=" \n ".join(node_info.get_all_names()))

        self.add_text_for_out_relation(node_info.node_id)
        self.add_text_for_in_relation(node_info.node_id)

    def add_text_for_out_relation(self, node_id):
        out_relation_infos = self.graph_data_reader.get_all_out_relation_infos(node_id=node_id)
        related_sentences_text = []
        for relation_info in out_relation_infos:
            end_node_info = relation_info.end_node_info
            # relation_text = relation_info.relation_name + " " + end_node_info.get_main_name()
            relation_text = end_node_info.get_main_name()
            if relation_text is None:
                pass
            else:
                related_sentences_text.append(relation_text)

        join_relation_text = " .\n ".join(related_sentences_text)
        self.doc_collection.add_field_to_doc(doc_id=node_id, field_name="out_relations",
                                             value=join_relation_text)

    def add_text_for_in_relation(self, node_id):

        relation_infos = self.graph_data_reader.get_all_in_relation_infos(node_id=node_id)
        related_sentences_text = []
        for relation_info in relation_infos:
            try:
                start_node_info = relation_info.start_node_info
                # relation_text = start_node_info.get_main_name() + " " + relation_info.relation_name
                relation_text = start_node_info.get_main_name()
                if relation_text is None:
                    pass
                else:
                    related_sentences_text.append(relation_text)
            except:
                print("add text error:%r" % start_node_info)
                traceback.print_exc()
        join_relation_text = " .\n ".join(related_sentences_text)
        self.doc_collection.add_field_to_doc(doc_id=node_id, field_name="in_relations",
                                             value=join_relation_text)

    def clean_comment(self, description):
        try:
            sent = BeautifulSoup(description, "lxml").get_text()
            return sent.strip().strip("/*").strip("//").strip("*").strip()
        except Exception:
            traceback.print_exc()
            return ""

    def build_doc_for_domain_entity(self, node_info: DomainEntityNodeInfo):
        mention_relation_type = ["mention in comment", "mention in inside comment", "mention in short description",
                                 "mention in string literal"]
        all_mention_relations = set()
        for relation_type in mention_relation_type:
            all_mention_relations.update(set(self.graph_data.get_relations(start_id=None, relation_type=relation_type,
                                                                           end_id=node_info.node_id)))
        all_mention_info = []

        for s, r, e in all_mention_relations:
            if r.startswith("mention"):
                start_node_info = self.graph_data_reader.get_node_info(s)
                mention = None
                if r == mention_relation_type[0]:
                    mention = start_node_info.properties.get("comment", "")
                elif r == mention_relation_type[1]:
                    mention = start_node_info.properties.get("inside comment", "")
                elif r == mention_relation_type[2]:
                    mention = start_node_info.properties.get("short_description", "")
                elif r == mention_relation_type[3]:
                    mention = start_node_info.properties.get("string_literal_expr", "")
                if isinstance(mention, list):
                    all_mention_info.extend(mention)
                else:
                    all_mention_info.append(mention)

        self.doc_collection.add_field_to_doc(doc_id=node_info.node_id, field_name="aliases",
                                             value="\n".join(node_info.get_all_names()))
        self.doc_collection.add_field_to_doc(doc_id=node_info.node_id, field_name="description",
                                             value=node_info.properties.get("descriptions_en", "") + " ".join(
                                                 all_mention_info))
        self.add_text_for_out_relation(node_info.node_id)
        self.add_text_for_in_relation(node_info.node_id)

    def clear(self):
        self.doc_collection = MultiFieldDocumentCollection()

    def build_doc(self):
        self.clear()
        print("start building doc")
        for id in self.graph_data.get_node_ids():
            node_info = self.graph_data_reader.get_node_info(id)
            try:
                if node_info is None:
                    continue
                # if node_info.get_main_name() is None:
                #     continue

                doc = MultiFieldDocument(id=node_info.node_id, name=node_info.get_main_name())
                self.doc_collection.add_document(doc)
                if "code" in node_info.properties.keys():
                    data = node_info.properties["code"]
                    self.doc_collection.add_field_to_doc(doc_id=node_info.node_id, field_name="doc",
                                                         value=data)
                if isinstance(node_info, CodeElementNodeInfo):
                    self.build_doc_for_code_element(node_info)
                elif isinstance(node_info, DomainEntityNodeInfo):
                    self.build_doc_for_domain_entity(node_info)
                elif isinstance(node_info, OperationEntityNodeInfo):
                    self.build_doc_for_operation_entity(node_info)
                elif isinstance(node_info, WikidataEntityNodeInfo):
                    self.build_doc_for_wikidata_entity(node_info)
                else:
                    self.build_doc_for_sentence(node_info)

            except:
                traceback.print_exc()
                print("build doc error %r" % node_info)

        print("end building doc")

    def build_doc_with_pure_code(self):
        print("start building doc")
        for id in self.graph_data.get_node_ids():
            node_info = self.graph_data_reader.get_node_info(id)
            try:
                if node_info is None:
                    continue
                if node_info.get_main_name() is None:
                    continue
                if "code" in node_info.properties.keys():
                    doc = MultiFieldDocument(id=node_info.node_id, name=node_info.get_main_name())
                    self.doc_collection.add_document(doc)
                    # processor = PureCodePreprocessor()
                    # data = " ".join(processor.clean(node_info.properties["code"]))
                    data = node_info.properties["code"]
                    self.doc_collection.add_field_to_doc(doc_id=node_info.node_id, field_name="doc",
                                                         value=data)
            except:
                traceback.print_exc()
                print("build doc error %r" % node_info)
        print("end building doc")

    def extract_kg_doc_collection_with_method(self, output_path, **config):
        print("start building doc")
        no_out_relation = False
        no_in_relation = False
        no_jdk = False
        method = False
        if "no_out_relation" in config.keys():
            no_out_relation = config["no_out_relation"]
        if "no_in_relation" in config.keys():
            no_in_relation = config["no_in_relation"]
        if "no_jdk" in config.keys():
            no_jdk = config["no_jdk"]
        if "with_method" in config.keys():
            method = config["with_method"]
        print("*" * 20)
        print("no_in_relation %r, no_out_relation %r, no_jdk %r, with_method %r" % (
            no_in_relation, no_out_relation, no_jdk, method))
        sub_doc_collection = MultiFieldDocumentCollection()
        graph_data_reader = GraphDataReader(graph_data=self.graph_data, node_info_factory=ProjectKGNodeInfoFactory())
        fail_count = 0
        for id in self.graph_data.get_node_ids():
            node_info = graph_data_reader.get_node_info(id)
            doc = self.doc_collection.get_by_id(id)
            if doc is None:
                fail_count = fail_count + 1
                continue
            new_doc = MultiFieldDocument(id=doc.id, name=doc.name)
            descriptions = []
            if not method and not no_jdk:
                descriptions = self.add_description(node_info, doc, no_out_relation, no_in_relation)
            if method and not no_jdk and "method" in node_info.labels:
                descriptions = self.add_description(node_info, doc, no_out_relation, no_in_relation)
            if not method and no_jdk and "jdk8" not in node_info.labels:
                descriptions = self.add_description(node_info, doc, no_out_relation, no_in_relation)
            if method and no_jdk and "method" in node_info.labels and "jdk8" not in node_info.labels:
                descriptions = self.add_description(node_info, doc, no_out_relation, no_in_relation)

            description = "\n".join([text for text in descriptions if text])
            new_doc.add_field("doc", description)
            if id % 2000 == 0:
                print("doc:%r" % description)
            sub_doc_collection.add_document(new_doc)
        sub_doc_collection.save(output_path)

    def add_description(self, node_info, doc, no_out_relation, no_in_relation=False):
        descriptions = []
        if isinstance(node_info, CodeElementNodeInfo):
            descriptions = self.add_one_description(node_info, doc, no_out_relation, no_in_relation)
        if isinstance(node_info, DomainEntityNodeInfo):
            descriptions = self.add_one_description(node_info, doc, no_out_relation, no_in_relation)
        if isinstance(node_info, OperationEntityNodeInfo):
            descriptions = self.add_one_description(node_info, doc, no_out_relation, no_in_relation)
        if isinstance(node_info, WikidataEntityNodeInfo):
            descriptions = self.add_one_description(node_info, doc, no_out_relation, no_in_relation)
        return descriptions

    def add_one_description(self, node_info, doc, no_out_relation, no_in_relation):
        descriptions = []
        descriptions.append(node_info.get_main_name())
        descriptions.append(doc.get_doc_text_by_field("aliases"))
        descriptions.append(doc.get_doc_text_by_field("description"))
        # descriptions.append(doc.get_doc_text_by_field("declare"))
        # descriptions.append(doc.get_doc_text_by_field("comment"))
        if no_out_relation:
            pass
        else:
            descriptions.append(doc.get_doc_text_by_field("out_relations"))
        if no_in_relation:
            pass
        else:
            descriptions.append(doc.get_doc_text_by_field("in_relations"))
        return descriptions

    def extract_kg_doc_collection(self, output_path):
        """
        extract the necessary field of text as a new doc
        :param output_path:
        :return:
        """
        sub_doc_collection = MultiFieldDocumentCollection()
        graph_data_reader = GraphDataReader(graph_data=self.graph_data, node_info_factory=ProjectKGNodeInfoFactory())
        fail_count = 0
        for id in self.graph_data.get_node_ids():
            node_info = graph_data_reader.get_node_info(id)
            doc = self.doc_collection.get_by_id(id)
            if doc is None:
                fail_count = fail_count + 1
                continue

            new_doc = MultiFieldDocument(id=doc.id, name=doc.name)

            descriptions = []
            if isinstance(node_info, CodeElementNodeInfo):
                descriptions.append(node_info.get_main_name())
                descriptions.append(doc.get_doc_text_by_field("aliases"))
                descriptions.append(doc.get_doc_text_by_field("out_relations"))
                descriptions.append(doc.get_doc_text_by_field("description"))

            if isinstance(node_info, DomainEntityNodeInfo):
                descriptions.append(node_info.get_main_name())
                descriptions.append(doc.get_doc_text_by_field("aliases"))
                descriptions.append(doc.get_doc_text_by_field("out_relations"))
                descriptions.append(doc.get_doc_text_by_field("description"))

            if isinstance(node_info, OperationEntityNodeInfo):
                descriptions.append(node_info.get_main_name())
                descriptions.append(doc.get_doc_text_by_field("aliases"))
                descriptions.append(doc.get_doc_text_by_field("out_relations"))
                descriptions.append(doc.get_doc_text_by_field("description"))

            if isinstance(node_info, WikidataEntityNodeInfo):
                descriptions.append(node_info.get_main_name())
                descriptions.append(doc.get_doc_text_by_field("aliases"))
                descriptions.append(doc.get_doc_text_by_field("out_relations"))
                descriptions.append(doc.get_doc_text_by_field("description"))

            description = "\n".join([text for text in descriptions if text])
            new_doc.add_field("doc", description)
            if id % 2000 == 0:
                print("doc:%r" % description)
            sub_doc_collection.add_document(new_doc)

        sub_doc_collection.save(output_path)

    def build_doc_for_kg(self, output_path=None):
        """
        build the doc for kg, only include aliases, out relation, description
        :return:
        """
        self.clear()
        self.build_doc()
        sub_doc_collection = MultiFieldDocumentCollection()
        graph_data_reader = GraphDataReader(graph_data=self.graph_data, node_info_factory=ProjectKGNodeInfoFactory())
        fail_count = 0
        for id in self.graph_data.get_node_ids():
            node_info = graph_data_reader.get_node_info(id)
            doc = self.doc_collection.get_by_id(id)
            if doc is None:
                fail_count = fail_count + 1
                continue

            new_doc = MultiFieldDocument(id=doc.id, name=doc.name)

            descriptions = []
            if isinstance(node_info, CodeElementNodeInfo):
                descriptions.append(node_info.get_main_name())
                descriptions.append(doc.get_doc_text_by_field("aliases"))
                descriptions.append(doc.get_doc_text_by_field("out_relations"))
                descriptions.append(doc.get_doc_text_by_field("description"))

            elif isinstance(node_info, DomainEntityNodeInfo):
                descriptions.append(node_info.get_main_name())
                descriptions.append(doc.get_doc_text_by_field("aliases"))
                descriptions.append(doc.get_doc_text_by_field("out_relations"))
                descriptions.append(doc.get_doc_text_by_field("description"))

            elif isinstance(node_info, OperationEntityNodeInfo):
                descriptions.append(node_info.get_main_name())
                descriptions.append(doc.get_doc_text_by_field("aliases"))
                descriptions.append(doc.get_doc_text_by_field("out_relations"))
                descriptions.append(doc.get_doc_text_by_field("description"))

            elif isinstance(node_info, WikidataEntityNodeInfo):
                descriptions.append(node_info.get_main_name())
                descriptions.append(doc.get_doc_text_by_field("aliases"))
                descriptions.append(doc.get_doc_text_by_field("out_relations"))
                descriptions.append(doc.get_doc_text_by_field("description"))
            else:
                descriptions.append(doc.get_doc_text_by_field("short_description_sentences"))
                descriptions.append(doc.get_doc_text_by_field("out_relations"))

            description = "\n".join([text for text in descriptions if text])
            new_doc.add_field("doc", description)
            if id % 2000 == 0:
                print("doc:%r" % description)
            sub_doc_collection.add_document(new_doc)
        if output_path is not None:
            sub_doc_collection.save(output_path)
        print("collection len{}".format(sub_doc_collection.get_num()))
        return sub_doc_collection

    def build_doc_for_sentence(self, node_info):
        self.doc_collection.add_field_to_doc(doc_id=node_info.node_id, field_name="short_description_sentences",
                                             value=node_info.properties["sentence_name"])
        self.add_text_for_out_relation(node_info.node_id)
        self.add_text_for_in_relation(node_info.node_id)

    def build_doc_for_operation_entity(self, node_info):
        self.doc_collection.add_field_to_doc(doc_id=node_info.node_id, field_name="aliases",
                                             value="\n".join(node_info.get_all_names()))
        self.add_text_for_out_relation(node_info.node_id)
        self.add_text_for_in_relation(node_info.node_id)

    def build_doc_for_wikidata_entity(self, node_info):
        self.doc_collection.add_field_to_doc(doc_id=node_info.node_id, field_name="aliases",
                                             value="\n".join(node_info.get_all_names()))
        self.add_text_for_out_relation(node_info.node_id)
        self.add_text_for_in_relation(node_info.node_id)
        self.doc_collection.add_field_to_doc(doc_id=node_info.node_id, field_name="description",
                                             value=node_info.properties.get("descriptions_en", ""))
