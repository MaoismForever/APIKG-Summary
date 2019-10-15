import copy
import re
import traceback

from sekg.constant.code import CodeEntityCategory
from sekg.constant.constant import PropertyConstant, DomainConstant, OperationConstance, WikiDataConstance
from sekg.graph.builder.code_kg_builder import CodeElementGraphDataBuilder
from sekg.graph.exporter.graph_data import GraphData
from sekg.ir.doc.wrapper import MultiFieldDocumentCollection

from util.annotation import catch_exception


class JDKKGFusion:
    """
    build the skeleton KG from the JavaParser analysis result for the Project Source Code.
    It will include the package, class, interface, method.
    """
    CHECK_CONSTANT_FILE_PATTERN = re.compile(r"[^A-Z_0-9]")

    def __init__(self):
        self.graph_data = GraphData()

    def select_name(self, terms):
        return min(terms, key=lambda x: len(x))

    def update_domain_node_alias(self, node_id, term):
        node_json = self.graph_data.get_node_info_dict(node_id=node_id)
        if not node_json:
            return GraphData.UNASSIGNED_NODE_ID
        node_properties = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]
        alias = node_properties[PropertyConstant.ALIAS]
        if type(alias) == set:
            alias.add(term)
        else:
            if term not in alias:
                alias.append(term)

        name = self.select_name(alias)
        node_json[DomainConstant.PRIMARY_PROPERTY_NAME] = name
        self.graph_data.update_node_index(node_id=node_id)
        return node_id

    def update_operation_node_alias(self, node_id, term):
        node_json = self.graph_data.get_node_info_dict(node_id=node_id)
        if not node_json:
            return GraphData.UNASSIGNED_NODE_ID
        node_properties = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]
        alias = node_properties[PropertyConstant.ALIAS]
        if type(alias) == set:
            alias.add(term)
        else:
            if term not in alias:
                alias.append(term)
        name = self.select_name(alias)
        node_json[OperationConstance.PRIMARY_PROPERTY_NAME] = name
        self.graph_data.update_node_index(node_id=node_id)
        return node_id

    def fuse(self, base_graph_data, extra_graph_data):
        print("start fuse two graph data")

        print("Extra GraphData")
        extra_graph_data.print_graph_info()

        print("Base GraphData")
        base_graph_data.print_graph_info()
        self.graph_data = copy.deepcopy(base_graph_data)

        ## cache the map for adding relation
        extra_id_to_base_id_map = {}

        qualified_name_entity_types = {
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_CLASS),
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_PACKAGE),
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_METHOD),
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_INTERFACE),
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_EXCEPTION_CLASS),
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_ENUM_CLASS),
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_ERROR_CLASS),
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_ANNOTATION_CLASS),
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_CONSTRUCT_METHOD),
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_PRIMARY_TYPE),
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_BASE_OVERRIDE_METHOD),
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_FIELD_OF_CLASS),
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_ENUM_CONSTANTS)
        }

        qualified_name_with_description = {
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_PARAMETER),
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_RETURN_VALUE),
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_EXCEPTION_CONDITION),
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_FIELD),
            CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_VALUE),
        }

        domain_lemma_id = {}
        operation_lemma_id = {}

        for node_id in self.graph_data.get_node_ids_by_label(DomainConstant.LABEL_DOMAIN_TERM):
            node_json = self.graph_data.get_node_info_dict(node_id=node_id)
            if not node_json:
                continue
            node_properties = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]
            lemma = node_properties[PropertyConstant.LEMMA]
            domain_lemma_id[lemma] = node_id

        for node_id in self.graph_data.get_node_ids_by_label(OperationConstance.LABEL_OPERATION):
            node_json = self.graph_data.get_node_info_dict(node_id=node_id)
            if not node_json:
                continue
            node_properties = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]
            lemma = node_properties[PropertyConstant.LEMMA]
            operation_lemma_id[lemma] = node_id

        for extra_node_id in extra_graph_data.get_node_ids():
            node_json = extra_graph_data.get_node_info_dict(node_id=extra_node_id)
            if not node_json:
                continue
            try:
                merge_node_id = GraphData.UNASSIGNED_NODE_ID
                node_properties = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]
                node_labels = node_json[GraphData.DEFAULT_KEY_NODE_LABELS]

                if DomainConstant.LABEL_DOMAIN_TERM in node_labels:
                    lemma = node_properties[PropertyConstant.LEMMA]
                    if lemma in domain_lemma_id:
                        merge_node_id = self.update_domain_node_alias(domain_lemma_id[lemma], node_properties[
                            DomainConstant.PRIMARY_PROPERTY_NAME])
                    else:
                        merge_node_id = self.graph_data.add_node(node_labels=node_labels,
                                                                 node_properties=node_properties,
                                                                 primary_property_name=DomainConstant.PRIMARY_PROPERTY_NAME)

                if OperationConstance.LABEL_OPERATION in node_labels:
                    lemma = node_properties[PropertyConstant.LEMMA]
                    if lemma in operation_lemma_id:
                        merge_node_id = self.update_operation_node_alias(operation_lemma_id[lemma], node_properties[
                            OperationConstance.PRIMARY_PROPERTY_NAME])
                    else:
                        merge_node_id = self.graph_data.add_node(node_labels=node_labels,
                                                                 node_properties=node_properties,
                                                                 primary_property_name=OperationConstance.PRIMARY_PROPERTY_NAME)

                if DomainConstant.LABEL_DOMAIN_TERM not in node_labels and WikiDataConstance.LABEL_WIKIDATA in node_labels:
                    merge_node_id = self.graph_data.add_node(node_labels=node_labels,
                                                             node_properties=node_properties,
                                                             primary_property_name=WikiDataConstance.PRIMARY_PROPERTY_NAME)

                if qualified_name_entity_types & set(node_labels):
                    merge_node_id = self.graph_data.merge_node(node_labels=node_labels,
                                                               node_properties=node_properties,
                                                               primary_property_name="qualified_name")

                if qualified_name_with_description & set(node_labels):
                    merge_node_id = self.graph_data.merge_node_with_multi_primary_property(node_labels=node_labels,
                                                                                           node_properties=node_properties,
                                                                                           primary_property_names=[
                                                                                               "qualified_name",
                                                                                               "short_description"])

                if merge_node_id == GraphData.UNASSIGNED_NODE_ID:
                    print("fuse extra node:%d-%r to Graph fail" % (extra_node_id, node_json))
                    continue
                extra_id_to_base_id_map[extra_node_id] = merge_node_id
                if len(extra_id_to_base_id_map.keys()) % 10000 == 0:
                    print("add %d as %d" % (extra_node_id, merge_node_id))
                    print("complete %d transfer" % len(extra_id_to_base_id_map.keys()))
            except:
                print("error!!!%r" % node_json)
                traceback.print_exc()
        print("start fuse relation")
        for (start_id, relation_type, end_id) in extra_graph_data.get_relation_pairs_with_type():
            if start_id not in extra_id_to_base_id_map:
                print("start_id %r in extra graph data could not found map in base graph data" % (start_id))
                print(relation_type, extra_graph_data.get_node_info_dict(start_id))

                continue
            if end_id not in extra_id_to_base_id_map:
                print("end_id %r in extra graph data could not found map in base graph data" % (end_id))
                continue

            start_id_in_base = extra_id_to_base_id_map[start_id]
            end_id_in_base = extra_id_to_base_id_map[end_id]

            if start_id_in_base == GraphData.UNASSIGNED_NODE_ID:
                print("the map for start_id %r has problem" % (start_id))
                continue

            if end_id_in_base == GraphData.UNASSIGNED_NODE_ID:
                print("the map for end_id_in_base %r has problem" % (end_id))
                continue
            self.graph_data.add_relation(startId=start_id_in_base, endId=end_id_in_base, relationType=relation_type)
            # print("add relation %d -%r  %d" % (start_id, relation_type, end_id))

        print("end fuse")
        self.graph_data.print_graph_info()

    @catch_exception
    def build_use_jdk_constant_field_relation_from_code_doc(self, document_collection: MultiFieldDocumentCollection):
        builder = CodeElementGraphDataBuilder(self.graph_data)
        self.graph_data = builder.build_use_jdk_constant_field_relation_from_code_doc(document_collection)
        return self.graph_data

    def save(self, graph_data_path):
        self.graph_data.save(graph_data_path)
