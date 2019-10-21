import json
import re
import traceback
from pathlib import Path

from nltk.corpus import stopwords
from nltk.corpus import wordnet as wn
from sekg.constant.code import CodeEntityCategory, CodeEntityRelationCategory
from sekg.constant.constant import PropertyConstant, DomainConstant, OperationConstance
from sekg.graph.exporter.graph_data import GraphData
from sekg.term.fusion import Fusion
from sekg.text.extractor.domain_entity.entity_extractor import EntityExtractor
from sekg.text.extractor.domain_entity.identifier_util import IdentifierInfoExtractor
from sekg.text.extractor.domain_entity.relation_detection import RelationType, RelationDetector
from sekg.util.code import ConceptElementNameUtil


class DomainKGFusion:
    """
    build the skeleton KG from the JavaParser analysis result for the Project Source Code.
    It will include the package, class, interface, method.
    """

    STOPLIST = set(stopwords.words('english'))

    METHOD_LABELS = {
        CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_METHOD),
        CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_BASE_OVERRIDE_METHOD),
    }

    CLASS_LABELS = {
        CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_CLASS),
        CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_PACKAGE),
        CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_INTERFACE),
        CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_ENUM_CONSTANTS),
    }

    VARIABLE_LABELS = {
        CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_FIELD),
        CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_LOCAL_VARIABLE),
        CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_PARAMETER),
        CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_FIELD_OF_CLASS),
    }

    def __init__(self):
        self.graph_data = GraphData()
        self.text_extractor = EntityExtractor()
        self.detector = RelationDetector()
        self.identifier_info_extractor = IdentifierInfoExtractor()

    def init_graph_data(self, graph_data_path):
        self.graph_data = GraphData.load(graph_data_path)

    def add_code_relation(self, start_node_id, relation_name, code_element):
        name = code_element.split("<")[0].split(".")[-1].split(" ")[-1]
        if len(name) == 0:
            return
        node_json = self.graph_data.find_one_node_by_property(PropertyConstant.ALIAS, name)
        if node_json is None:
            return
        end_node_id = node_json[GraphData.DEFAULT_KEY_NODE_ID]
        self.graph_data.add_relation(startId=start_node_id,
                                     relationType=relation_name,
                                     endId=end_node_id)

    def handle_comment_in_class(self, node_id, node_properties):
        terms = set()
        linkages = set()

        comment = node_properties.get(PropertyConstant.COMMENT, "")
        domain_terms, code_elements = self.text_extractor.extract_from_comment(comment)
        for term in domain_terms:
            terms.add(term)
            linkages.add((node_id, RelationType.MENTION_IN_COMENT.value, term))

        return terms, linkages

    def handle_text_in_method(self, node_id, node_properties):
        terms = set()
        linkages = set()

        comment = node_properties.get(PropertyConstant.COMMENT, "")
        domain_terms, code_elements = self.text_extractor.extract_from_comment(comment)
        for term in domain_terms:
            terms.add(term)
            linkages.add((node_id, RelationType.MENTION_IN_COMENT.value, term))
        for element in code_elements:
            self.add_code_relation(node_id, RelationType.MENTION_IN_COMENT.value, element)

        for inside_comment in node_properties.get(PropertyConstant.INSIDE_COMMENT, []):
            domain_terms, code_elements = self.text_extractor.extract_from_sentence(inside_comment)
            for term in domain_terms:
                terms.add(term)
                linkages.add((node_id, RelationType.MENTION_IN_INSIDE_COMENT.value, term))
            for element in code_elements:
                self.add_code_relation(node_id, RelationType.MENTION_IN_INSIDE_COMENT.value, element)

        for literal_expr in node_properties.get(PropertyConstant.STRING_LITERAL_EXPR, []):

            domain_terms, code_elements = self.text_extractor.extract_from_comment(literal_expr)
            for term in domain_terms:
                terms.add(term)
                linkages.add((node_id, RelationType.MENTION_IN_STRING_LITERAL.value, term))
            for element in code_elements:
                self.add_code_relation(node_id, RelationType.MENTION_IN_STRING_LITERAL.value, element)

        return terms, linkages

    def handle_description(self, node_id, description):
        terms = set()
        linkages = set()

        domain_terms, code_elements = self.text_extractor.extract_from_sentence(description)
        for term in domain_terms:
            linkages.add((node_id, RelationType.MENTION_IN_SHORT_DESCRIPTION.value, term))
        for element in code_elements:
            self.add_code_relation(node_id, RelationType.MENTION_IN_SHORT_DESCRIPTION.value, element)
        return terms, linkages

    def handle_method_name(self, node_id, name):

        terms, operations, relations, linkages = self.identifier_info_extractor.extract_from_method_name(
            name, mark_for_identifier_in_relation=node_id)

        belong_to_relations = self.graph_data.get_relations(node_id, CodeEntityRelationCategory.to_str(
            CodeEntityRelationCategory.RELATION_CATEGORY_BELONG_TO))
        if len(belong_to_relations) > 0:
            class_id = belong_to_relations.pop()[2]
            for op in operations:
                linkages.add((class_id, RelationType.HAS_OPERATION.value, op))

        return terms, operations, relations, linkages

    def handle_class_name(self, node_id, name):
        terms, relations, linkages = self.identifier_info_extractor.extract_from_class_name(name,
                                                                                            mark_for_identifier_in_relation=node_id)

        return terms, relations, linkages

    def handle_variable_name(self, node_id, name):
        terms, relations, linkages = self.identifier_info_extractor.extract_from_variable(name,
                                                                                          mark_for_identifier_in_relation=node_id)

        return terms, relations, linkages

    def extract_term_and_relation(self, term_save_path=None, operation_save_path=None, term_relation_save_path=None,
                                  linkage_save_path=None, term_aliases_save_path=None, not_fused_term_save_path=None):
        print("start extract term and relation from graph data")
        self.graph_data.print_graph_info()

        # cache the map for adding relation
        not_fused_terms = set()
        operations = set()
        relations = set()
        linkages = set()
        i = 0
        for node_id in list(self.graph_data.get_node_ids()):
            try:
                i = i + 1
                if (i % 100) == 0:
                    print("已经执行了%d次节点检索" % i)
                # else:
                #     i = i + 1
                node_json = self.graph_data.get_node_info_dict(node_id=node_id)
                if not node_json:
                    continue

                node_properties = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]
                node_labels = node_json[GraphData.DEFAULT_KEY_NODE_LABELS]

                # print(len(node_labels & self.METHOD_LABELS))

                if 'sentence' in node_labels:
                    terms_, linkages_ = self.handle_description(node_id, node_properties["sentence_name"])
                    not_fused_terms.update(terms_)
                    linkages.update(linkages_)
                    continue

                if len(node_labels & self.METHOD_LABELS) > 0:
                    terms_, linkages_ = self.handle_text_in_method(node_id, node_properties)
                    not_fused_terms.update(terms_)
                    linkages.update(linkages_)

                    terms_, operations_, relations_, linkages_ = self.handle_method_name(node_id, node_properties[
                        GraphData.DEFAULT_KEY_PROPERTY_QUALIFIED_NAME])
                    not_fused_terms.update(terms_)
                    operations.update(operations_)
                    relations.update(relations_)
                    linkages.update(linkages_)

                description = node_properties.get(PropertyConstant.DESCRIPTION, "")
                if description is not None and len(description) > 0:
                    terms_, linkages_ = self.handle_description(node_id, node_properties[PropertyConstant.DESCRIPTION])
                    not_fused_terms.update(terms_)
                    linkages.update(linkages_)

                if len(node_labels & self.CLASS_LABELS) > 0:
                    terms_, linkages_ = self.handle_comment_in_class(node_id, node_properties)
                    not_fused_terms.update(terms_)
                    linkages.update(linkages_)

                    terms_, relations_, linkages_ = self.handle_class_name(node_id, node_properties[
                        GraphData.DEFAULT_KEY_PROPERTY_QUALIFIED_NAME])
                    not_fused_terms.update(terms_)
                    linkages.update(linkages_)
                    relations.update(relations_)

                if len(node_labels & self.VARIABLE_LABELS) > 0:
                    terms_, linkages_ = self.handle_comment_in_class(node_id, node_properties)
                    not_fused_terms.update(terms_)
                    linkages.update(linkages_)

                    terms_, relations_, linkages_ = self.handle_variable_name(node_id, node_properties[
                        GraphData.DEFAULT_KEY_PROPERTY_QUALIFIED_NAME])
                    not_fused_terms.update(terms_)
                    linkages.update(linkages_)
                    relations.update(relations_)

            except:
                traceback.print_exc()
        new_terms = []
        for term in not_fused_terms:
            if self.valid_term(term):
                new_terms.append(term)
        not_fused_terms = set(new_terms)

        relations_ = self.detector.detect_relation_by_starfix(not_fused_terms)
        relations.update(relations_)

        print("complete domain extraction")
        term_fusion = Fusion()
        synsets = term_fusion.fuse_by_synonym(not_fused_terms)
        print("complete synonym fusion")

        fused_term_to_aliases_map = {}
        for synset in synsets:
            fused_term_to_aliases_map[synset.key] = list(synset.terms)

        fused_terms = fused_term_to_aliases_map.keys()

        new_relations = set()
        new_linkages = set()

        for start_e, relation_name, end_e in relations:
            if relation_name == "has operation":
                continue
            if relation_name == "can be operated":
                continue
            new_start_e_list = set()
            new_end_e_list = set()

            for fused_term, aliases in fused_term_to_aliases_map.items():
                if end_e in aliases:
                    new_end_e_list.add(fused_term)
                if start_e in aliases:
                    new_start_e_list.add(fused_term)

            for new_start_e in new_start_e_list:
                for new_end_e in new_end_e_list:
                    new_relations.add((new_start_e, relation_name, new_end_e))

            if len(new_start_e_list) == 0:
                new_start_e_list.add(start_e)
            if len(new_end_e_list) == 0:
                new_end_e_list.add(end_e)
        relations = new_relations

        for start_e, relation_name, end_e in linkages:
            if relation_name == "has operation":
                continue
            if relation_name == "can be operated":
                continue

            new_start_e_list = set()
            new_end_e_list = set()

            for fused_term, aliases in fused_term_to_aliases_map.items():
                if end_e in aliases:
                    new_end_e_list.add(fused_term)
                if start_e in aliases:
                    new_start_e_list.add(fused_term)
            if len(new_start_e_list) == 0:
                new_start_e_list.add(start_e)
            if len(new_end_e_list) == 0:
                new_end_e_list.add(end_e)

            for new_start_e in new_start_e_list:
                for new_end_e in new_end_e_list:
                    new_linkages.add((new_start_e, relation_name, new_end_e))

        linkages = new_linkages

        print("length of new_linkages %d" % (len(linkages)))

        # term_orgin = {k: list(v) for k, v in term_orgin.items()}

        import json

        if term_save_path is not None:
            with Path(term_save_path).open("w") as f:
                f.write("\n".join(sorted(fused_terms, key=lambda x: x)))

        if not_fused_term_save_path is not None:
            with Path(not_fused_term_save_path).open("w") as f:
                f.write("\n".join(sorted(not_fused_terms, key=lambda x: x)))

        if operation_save_path is not None:
            with Path(operation_save_path).open("w") as f:
                f.write("\n".join(sorted(operations, key=lambda x: x)))

        if term_relation_save_path is not None:
            with Path(term_relation_save_path).open("w") as f:
                json.dump(
                    [(r[0], str(r[1]), r[2]) for r in relations if self.valid_term(r[0]) and self.valid_term(r[2])], f,
                    indent=4)

        if linkage_save_path is not None:
            with Path(linkage_save_path).open("w") as f:
                json.dump([(r[0], str(r[1]), r[2]) for r in linkages if self.valid_term(r[0]) or self.valid_term(r[2])],
                          f, indent=4)

        if term_aliases_save_path is not None:
            with Path(term_aliases_save_path).open("w") as f:
                json.dump(fused_term_to_aliases_map,
                          f, indent=4)

        return fused_terms, operations, relations, linkages, fused_term_to_aliases_map

    def select_name(self, terms):
        return min(terms, key=lambda x: len(x))

    def valid_term(self, term):
        term = str(term)
        if len(term) <= 2 or term.isdigit() or (len(term) > 30 and len(term.split()) > 4):
            return False
        prefix, *rest = term.split()
        if prefix in self.STOPLIST:
            return False
        return True

    def add_domain_term(self, term, lemma, aliases):
        """
        add a new term to graph data
        :param term: the term added to GraphData
        :return: the node_id fo the added term node
        """
        if aliases == None:
            aliases = set([])
        else:
            aliases = set(list(aliases))
        aliases.add(lemma)
        aliases.add(term)

        node_labels = [DomainConstant.LABEL_DOMAIN_TERM]
        node_properties = {
            DomainConstant.PRIMARY_PROPERTY_NAME: term,
            PropertyConstant.ALIAS: aliases,
            PropertyConstant.LEMMA: lemma
        }
        domain_term_node_id = self.graph_data.add_node(node_labels=node_labels,
                                                       node_properties=node_properties,
                                                       primary_property_name=DomainConstant.PRIMARY_PROPERTY_NAME)
        return domain_term_node_id

    def add_operation(self, op, lemma):
        node_labels = [OperationConstance.LABEL_OPERATION]
        node_properties = {
            OperationConstance.PRIMARY_PROPERTY_NAME: op,
            PropertyConstant.ALIAS: {op},
            PropertyConstant.LEMMA: lemma
        }
        operation_node_id = self.graph_data.add_node(node_labels=node_labels,
                                                     node_properties=node_properties,
                                                     primary_property_name=OperationConstance.PRIMARY_PROPERTY_NAME)
        return operation_node_id

    def update_domain_node_alias(self, node_id, term):
        node_json = self.graph_data.get_node_info_dict(node_id=node_id)
        if not node_json:
            return
        node_properties = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]
        alias = node_properties[PropertyConstant.ALIAS]
        alias.add(term)
        name = self.select_name(alias)
        node_json[DomainConstant.PRIMARY_PROPERTY_NAME] = name
        self.graph_data.update_node_index(node_id=node_id)

    def update_operation_node_alias(self, node_id, term):
        node_json = self.graph_data.get_node_info_dict(node_id=node_id)
        if not node_json:
            return
        node_properties = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]
        alias = node_properties[PropertyConstant.ALIAS]
        alias.add(term)
        name = self.select_name(alias)
        node_json[OperationConstance.PRIMARY_PROPERTY_NAME] = name
        self.graph_data.update_node_index(node_id=node_id)

    def add_relation_for_same_name_operation_and_domain_term(self):
        operation_node_ids = self.graph_data.get_node_ids_by_label(OperationConstance.LABEL_OPERATION)

        for operation_id in operation_node_ids:
            operation_node = self.graph_data.get_node_info_dict(operation_id)

            operation_name = operation_node[GraphData.DEFAULT_KEY_NODE_PROPERTIES][
                OperationConstance.PRIMARY_PROPERTY_NAME]

            domain_term_node = self.graph_data.find_one_node_by_property(
                property_name=DomainConstant.PRIMARY_PROPERTY_NAME, property_value=operation_name)

            if domain_term_node == None:
                continue
            domain_term_node_id = domain_term_node[GraphData.DEFAULT_KEY_NODE_ID]

            self.graph_data.add_relation(operation_id, "corresponding concept", domain_term_node_id)
            self.graph_data.add_relation(domain_term_node_id, "corresponding operation", operation_id)

    def save(self, graph_data_path):
        self.graph_data.save(graph_data_path)

    def fuse(self, terms, operations, relations, linkages, aliases_map):
        """
        start import the term and their relation to graph
        :param term_origins:
        :param term_relations:
        :return:
        """
        # domain_graph_data = GraphData()

        self.graph_data.create_index_on_property(DomainConstant.PRIMARY_PROPERTY_NAME)
        self.graph_data.create_index_on_property(OperationConstance.PRIMARY_PROPERTY_NAME)
        self.graph_data.create_index_on_property(PropertyConstant.ALIAS)

        # todo:update the index when add
        print("start fuse with domain knowledge")
        self.graph_data.print_graph_info()

        term_lemma2id = {}
        term_name2id = {}
        op_lemma2id = {}
        op_name2id = {}

        def __add_or_update(name, is_op=False):
            if is_op:
                lemma = name.lower()
                if lemma in op_lemma2id:
                    node_id = op_lemma2id[lemma]
                    self.update_operation_node_alias(node_id, name)
                else:
                    node_id = self.add_operation(name, lemma)
                    if node_id == GraphData.UNASSIGNED_NODE_ID:
                        print("adding operation %r fail" % name)
                        return node_id
                    op_lemma2id[lemma] = node_id
                op_name2id[name] = node_id
            else:
                lemma = name.replace("-", " ").replace("  ", " ").lower()
                lemma = re.sub('([^v])([0-9]+)', r'\1 \2', lemma)
                node_id = self.add_domain_term(name, lemma, aliases=aliases_map.get(name, None))

                if node_id == GraphData.UNASSIGNED_NODE_ID:
                    print("adding domain term %r fail" % name)
                    return node_id
                term_lemma2id[lemma] = node_id
                term_name2id[name] = node_id
            return node_id

        for term in sorted(terms, key=lambda x: len(x.split())):
            __add_or_update(term)

        for op in operations:
            __add_or_update(op, is_op=True)

        def __add_relation(start_term, relation_name, end_term):
            start_name2id = term_name2id
            end_name2id = term_name2id
            start_term_is_op = False
            end_term_is_op = False
            # if relation_name.startswith("operation_"):
            #     start_name2id = op_name2id
            #     start_term_is_op = True
            if relation_name == "has operation":
                end_name2id = op_name2id
                end_term_is_op = True
            if relation_name == "instance of":
                end_name2id = op_name2id
                end_term_is_op = True
            if relation_name == "can be operated":
                end_name2id = op_name2id
                end_term_is_op = True

            if type(start_term) == int:
                start_node_id = start_term
            else:
                if start_term in start_name2id:
                    start_node_id = start_name2id[start_term]
                else:
                    start_node_id = __add_or_update(start_term, is_op=start_term_is_op)
                if start_node_id == GraphData.UNASSIGNED_NODE_ID:
                    print("adding start_domain term %r fail for relation %r" % (
                        start_term, (start_term, relation_name, end_term)))
                    return
            if type(end_term) == int:
                end_node_id = end_term
            else:
                if end_term in end_name2id:
                    end_node_id = end_name2id[end_term]
                else:
                    end_node_id = __add_or_update(end_term, is_op=end_term_is_op)
                if end_node_id == GraphData.UNASSIGNED_NODE_ID:
                    print("adding start_domain term %r fail for relation %r" % (
                        start_term, (start_term, relation_name, end_term)))
                    return

            self.graph_data.add_relation(startId=start_node_id,
                                         relationType=relation_name,
                                         endId=end_node_id)

        for (start_term, relation_name, end_term) in relations:
            __add_relation(start_term, relation_name, end_term)

        for (start_term, relation_name, end_term) in linkages:
            __add_relation(start_term, relation_name, end_term)

        isA_relations = set()
        for (start_id, _, end_id) in self.graph_data.get_relations(
                relation_type=CodeEntityRelationCategory.to_str(CodeEntityRelationCategory.RELATION_CATEGORY_EXTENDS)):
            start_domain_ids = {e for _, _, e in self.graph_data.get_relations(start_id=start_id,
                                                                               relation_type=RelationType.REPRESENT.value)}
            end_domain_ids = {e for _, _, e in self.graph_data.get_relations(start_id=start_id,
                                                                             relation_type=RelationType.REPRESENT.value)}
            for s in start_domain_ids:
                for e in end_domain_ids:
                    isA_relations.add((s, RelationType.IS_A.value, e))
        for r in isA_relations:
            __add_relation(*r)

        self.add_relation_for_same_name_operation_and_domain_term()
        print("end fuse with domain knowledge")
        self.graph_data.refresh_indexer()
        self.graph_data.print_graph_info()

    def build_aliases_for_domain_term_and_operations(self, new_all_aliases_save_path=None):
        name_util = ConceptElementNameUtil()
        domain_term_ids = self.graph_data.get_node_ids_by_label(DomainConstant.LABEL_DOMAIN_TERM)
        term_name_list = []
        fused_term_to_aliases_map = {}

        for domain_term_id in domain_term_ids:
            node_json = self.graph_data.get_node_info_dict(domain_term_id)
            term_name = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES][DomainConstant.PRIMARY_PROPERTY_NAME]
            term_name_list.append(term_name)

        for domain_term_id in domain_term_ids:
            node_json = self.graph_data.get_node_info_dict(domain_term_id)
            term_name = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES][DomainConstant.PRIMARY_PROPERTY_NAME]

            all_aliases_list = set([])

            generated_aliases = name_util.generate_aliases(term_name, vocabulary=term_name_list)
            all_aliases_list = all_aliases_list | set(generated_aliases)

            exist_aliases = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES].get(PropertyConstant.ALIAS, set([]))

            for alias in exist_aliases:
                all_aliases_list.add(alias)
                generated_aliases = name_util.generate_aliases(term_name, vocabulary=term_name_list)
                all_aliases_list = all_aliases_list | set(generated_aliases)

            node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES][PropertyConstant.ALIAS] = all_aliases_list
            fused_term_to_aliases_map[term_name] = list(all_aliases_list)

        operation_ids = self.graph_data.get_node_ids_by_label(OperationConstance.LABEL_OPERATION)
        # todo: build the relation between operation and domain term
        for operation_id in operation_ids:
            node_json = self.graph_data.get_node_info_dict(operation_id)
            term_name = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES][OperationConstance.PRIMARY_PROPERTY_NAME]

            synsets = wn.synsets(term_name, pos="v")
            generated_aliases = [synset.name().split(".")[0] for synset in synsets]

            exist_aliases = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES].get(PropertyConstant.ALIAS, set([]))
            for alias in generated_aliases:
                exist_aliases.add(alias)

            node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES][PropertyConstant.ALIAS] = exist_aliases

        if new_all_aliases_save_path != None:
            with Path(new_all_aliases_save_path).open("w") as f:
                json.dump(fused_term_to_aliases_map,
                          f, indent=4)

        # todo: build the aliases for operation
        self.graph_data.refresh_indexer()

    def delete_islocated_nodes_by_label(self, label):
        domain_node_ids = self.graph_data.get_node_ids_by_label(label)
        remove_ids = []
        for domain_id in domain_node_ids:
            out_ids = self.graph_data.get_all_out_relations(domain_id)
            in_ids = self.graph_data.get_all_in_relations(domain_id)
            if not out_ids and not in_ids:
                remove_ids.append(domain_id)
        print("delete %d islocated domain term" % (len(remove_ids)))
        for id in remove_ids:
            # print("remove islocated node:", self.graph_data.get_node_info_dict(id))
            self.graph_data.remove_node(id)
        return self.graph_data

    def delete_nodes_and_relations(self, name_list):
        for name in name_list:
            node_info = self.graph_data.find_one_node_by_property(DomainConstant.PRIMARY_PROPERTY_NAME, name)
            if node_info:
                node_id = node_info["id"]
                out_relations = self.graph_data.get_all_out_relations(node_id)
                in_relations = self.graph_data.get_all_in_relations(node_id)
                for s, r, e in out_relations.union(in_relations):
                    # print('delete relation %d, %s, %d' % (s, r, e))
                    self.graph_data.remove_relation(s, r, e)
                self.graph_data.remove_node(node_id)
                # print("delete node %d" % (node_id))
            else:
                print("can't find node for %s" % (name))
        return self.graph_data

    # def filter_domain_by_name_length(self, name_length=30, name_split_number=3):
    #     domain_ids = self.graph_data.get_node_ids_by_label(DomainConstant.LABEL_DOMAIN_TERM)
    #     remove_nodes = []
    #     for node_id in domain_ids:
    #         node_info = self.graph_data.get_node_info_dict(node_id)
    #         term_name = node_info[GraphData.DEFAULT_KEY_NODE_PROPERTIES][DomainConstant.PRIMARY_PROPERTY_NAME]
    #         if len(term_name) > name_length and len(term_name.split(" ")) > name_split_number:
    #             out_relations = self.graph_data.get_all_out_relations(node_id)
    #             in_relations = self.graph_data.get_all_in_relations(node_id)
    #             for s, r, e in out_relations.union(in_relations):
    #                 # print('delete relation %d, %s, %d' % (s, r, e))
    #                 self.graph_data.remove_relation(s, r, e)
    #             remove_nodes.append(node_id)
    #     for node_id in remove_nodes:
    #         self.graph_data.remove_node(node_id)
