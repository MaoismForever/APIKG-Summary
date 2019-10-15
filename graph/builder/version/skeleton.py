import copy
import json

from sekg.constant.code import CodeEntityCategory, CodeEntityRelationCategory
from sekg.graph.builder.code_kg_builder import CodeElementGraphDataBuilder
from sekg.graph.creator import NodeBuilder
from sekg.graph.exporter.graph_data import GraphData


class SkeletonKGBuilder:
    """
    build the skeleton KG from the JavaParser analysis result for the Project Source Code.
    It will include the package, class, interface, method.
    """

    def __init__(self):
        self.graph_data = GraphData()
        self.code_element_kg_builder = CodeElementGraphDataBuilder(self.graph_data)

    def init_graph_data(self, graph_data_path):
        self.graph_data = GraphData.load(graph_data_path)
        self.code_element_kg_builder = CodeElementGraphDataBuilder(self.graph_data)

    def import_primary_type(self):

        type_list = CodeEntityCategory.java_primary_types()

        for item in type_list:
            code_element = {
                "qualified_name": item["name"],
                "api_type": CodeEntityCategory.CATEGORY_PRIMARY_TYPE,
                "short_description": item["description"]
            }
            cate_labels = CodeEntityCategory.to_str_list(code_element["api_type"])

            builder = NodeBuilder()
            builder = builder.add_property(**code_element).add_entity_label().add_labels("code_element", *cate_labels)

            self.graph_data.add_node(
                node_id=GraphData.UNASSIGNED_NODE_ID,
                node_labels=builder.get_labels(),
                node_properties=builder.get_properties(),
                primary_property_name="qualified_name")

        self.graph_data.print_graph_info()

    def import_normal_entity_json(self, entity_json_path):
        print("start import normal entity json")
        with open(entity_json_path, "r", encoding='UTF-8') as f:
            code_list = json.load(f)
        record_num = len(code_list)
        print("load json complete size=%d" % record_num)

        fail_num = 0
        name_mark = set([])
        for index, code_element in enumerate(code_list):
            format_qualified_name = self.code_element_kg_builder.format_qualified_name(code_element["qualified_name"])
            if not format_qualified_name:
                print("not __valid name %r" % code_element["qualified_name"])
                fail_num += 1
                continue
            code_element["qualified_name"] = format_qualified_name
            if code_element["qualified_name"] in name_mark:
                continue
            name_mark.add(code_element["qualified_name"])

            code_element.pop("qualified_name")

            node_id = self.code_element_kg_builder.add_normal_code_element_entity(format_qualified_name,
                                                                                  code_element["type"], **code_element)

        print("total=%d fail_num=%d success_num=%d" % (record_num, fail_num, record_num - fail_num))
        self.graph_data.print_graph_info()

        print("end import normal entity json")

    def import_normal_entity_relation_json(self, entity_relation_json_path):
        print("start import normal entity relations json")
        print(self.graph_data)
        self.graph_data.print_label_count()

        with open(entity_relation_json_path, "r", encoding='UTF-8') as f:
            code_relation_list = json.load(f)
            record_num = len(code_relation_list)
            print("load json complete size=%d" % record_num)

        fail_num = 0
        for relation_json in code_relation_list:
            relation_type = relation_json["relation_type"]

            if relation_type == CodeEntityRelationCategory.RELATION_CATEGORY_METHOD_IMPLEMENT_CODE_CALL_METHOD:
                success = self.code_element_kg_builder.add_method_call_relation(relation_json["start_name"],
                                                                                relation_json["end_name"])
                if success == False:
                    fail_num = fail_num + 1
                continue
            if relation_type == relation_type == CodeEntityRelationCategory.RELATION_CATEGORY_METHOD_IMPLEMENT_CODE_USE_CLASS:
                continue

            if relation_type == CodeEntityRelationCategory.RELATION_CATEGORY_BELONG_TO or relation_type == CodeEntityRelationCategory.RELATION_CATEGORY_EXTENDS or relation_type == CodeEntityRelationCategory.RELATION_CATEGORY_IMPLEMENTS:
                success = self.code_element_kg_builder.add_relation_by_creating_not_exist_entity(
                    relation_json["start_name"],
                    relation_json["end_name"],
                    relation_type=relation_type

                )
                if success == False:
                    fail_num = fail_num + 1
                continue

            success = self.code_element_kg_builder.add_relation_by_not_creating_entity(relation_json["start_name"],
                                                                                       relation_json["end_name"],
                                                                                       relation_type)

            if success == False:
                fail_num = fail_num + 1

        print("fail num=%d" % fail_num)
        self.graph_data.print_graph_info()

        print("end import normal entity relations json")

    def import_field_entity(self, entity_json_path, entity_relation_json_path):

        print("start import field entity json")
        print(self.graph_data)
        self.graph_data.print_label_count()

        with open(entity_json_path, "r", encoding='UTF-8') as f:
            code_list = json.load(f)
            record_num = len(code_list)
        print("load json complete size=%d" % record_num)

        with open(entity_relation_json_path, "r", encoding='UTF-8') as f:
            relation_list = json.load(f)
            relation_num = len(relation_list)
            print("load json complete entity relation size=%d" % relation_num)
        old_id_to_new_node_id_map = {}

        for index, code_element in enumerate(code_list):
            field_id = code_element["id"]
            field_type = code_element["field_type"]
            field_name = code_element["field_name"]
            # short_description = code_element["description"]
            short_description = ""  # the field json has not description

            new_field_node_id = self.code_element_kg_builder.add_base_value_entity_node(value_type=field_type,
                                                                                        value_name=field_name,
                                                                                        short_description=short_description,
                                                                                        entity_category=CodeEntityCategory.CATEGORY_FIELD)

            old_id_to_new_node_id_map[field_id] = new_field_node_id

        for r in relation_list:
            field_node_id = old_id_to_new_node_id_map[r["field_id"]]
            class_qualified_name = self.code_element_kg_builder.format_qualified_name(r["belong_class_interface_name"])
            node_json = self.graph_data.find_one_node_by_property("qualified_name", class_qualified_name)
            if node_json is None:
                parent_node_id = self.code_element_kg_builder.add_type_node(class_qualified_name)

            else:
                parent_node_id = node_json[GraphData.DEFAULT_KEY_NODE_ID]

            if self.graph_data.exist_relation(parent_node_id,
                                              CodeEntityRelationCategory.to_str(
                                                  CodeEntityRelationCategory.RELATION_CATEGORY_HAS_FIELD),
                                              field_node_id):
                print("------")
                print(r, field_node_id, node_json)

            self.graph_data.add_relation(parent_node_id,
                                         CodeEntityRelationCategory.to_str(
                                             CodeEntityRelationCategory.RELATION_CATEGORY_HAS_FIELD),
                                         field_node_id)

        self.graph_data.print_graph_info()

        print("end import field entity json")

    def import_parameter_entity(self, entity_json_path, entity_relation_json_path):
        print("start import parameter entity")
        self.graph_data.print_graph_info()

        with open(entity_json_path, "r", encoding='UTF-8') as f:
            code_list = json.load(f)
            record_num = len(code_list)
            print("load json complete entity size=%d" % record_num)

        with open(entity_relation_json_path, "r", encoding='UTF-8') as f:
            relation_list = json.load(f)
            record_num = len(relation_list)
            print("load json complete entity relation size=%d" % record_num)

        old_id_to_new_node_id_map = {}

        for index, code_element in enumerate(code_list):
            parameter_id = code_element["id"]
            parameter_type = code_element["parameter_type"]
            parameter_name = code_element["parameter_name"]

            short_description = code_element["description"]
            parameter_node_id = self.code_element_kg_builder.add_base_value_entity_node(value_type=parameter_type,
                                                                                        value_name=parameter_name,
                                                                                        short_description=short_description,
                                                                                        entity_category=CodeEntityCategory.CATEGORY_PARAMETER)

            old_id_to_new_node_id_map[parameter_id] = parameter_node_id

        for r in relation_list:
            parameter_node_id = old_id_to_new_node_id_map[r["parameter_id"]]
            method_qualified_name = self.code_element_kg_builder.format_qualified_name(r["method_name"])

            if not method_qualified_name:
                print("not __valid method name %r" % method_qualified_name)

                continue
            node_json = self.graph_data.find_one_node_by_property("qualified_name", method_qualified_name)
            if not node_json:
                print("can't find %r, creating" % method_qualified_name)
                method_node_id = self.code_element_kg_builder.add_method_node(
                    method_qualified_name=method_qualified_name)

            else:
                method_node_id = node_json[GraphData.DEFAULT_KEY_NODE_ID]

            self.graph_data.add_relation(method_node_id,
                                         CodeEntityRelationCategory.to_str(
                                             CodeEntityRelationCategory.RELATION_CATEGORY_HAS_PARAMETER),
                                         parameter_node_id)

        print("end import parameter entity json")
        self.graph_data.print_graph_info()

    def import_method_local_variable_entity(self, entity_json_path):
        self.graph_data.print_graph_info()
        print("start import method local variable entity")
        with open(entity_json_path, "r", encoding='UTF-8') as f:
            code_list = json.load(f)
            record_num = len(code_list)
            print("load json complete entity size=%d" % record_num)

        for index, variable_infos in enumerate(code_list):

            method_qualified_name = variable_infos["method_name"]
            method_qualified_name = self.code_element_kg_builder.format_qualified_name(method_qualified_name)
            if not method_qualified_name:
                print("not __valid method name %r" % method_qualified_name)

                continue
            node_json = self.graph_data.find_one_node_by_property("qualified_name", method_qualified_name)
            if not node_json:
                print("can't find %r, creating" % method_qualified_name)
                method_node_id = self.code_element_kg_builder.add_method_node(
                    method_qualified_name=method_qualified_name)

            else:
                method_node_id = node_json[GraphData.DEFAULT_KEY_NODE_ID]

            for variable in variable_infos["variable_model_list"]:
                variable_type = variable["type"]
                variable_name = variable["name"]
                variable_node_id = self.code_element_kg_builder.add_base_value_entity_node(value_type=variable_type,
                                                                                           value_name=variable_name,
                                                                                           short_description="",
                                                                                           entity_category=CodeEntityCategory.CATEGORY_LOCAL_VARIABLE)

                if variable_node_id == GraphData.UNASSIGNED_NODE_ID:
                    print("add variable node fail for %r" % variable)
                    continue
                self.graph_data.add_relation(method_node_id,
                                             CodeEntityRelationCategory.to_str(
                                                 CodeEntityRelationCategory.RELATION_CATEGORY_USE_LOCAL_VARIABLE),
                                             variable_node_id)

        print("end import local variable entity json")
        self.graph_data.print_graph_info()

    def import_return_value_entity(self, entity_json_path, entity_relation_json_path):
        print("start import return value entity")
        with open(entity_json_path, "r", encoding='UTF-8') as f:
            code_list = json.load(f)
            record_num = len(code_list)
        print("load json complete size=%d" % record_num)

        with open(entity_relation_json_path, "r", encoding='UTF-8') as f:
            relation_list = json.load(f)
            record_num = len(relation_list)
            print("load json complete entity relation size=%d" % record_num)

        old_id_to_new_node_id_map = {}
        for index, code_element in enumerate(code_list):
            return_value_id = code_element["id"]
            return_value_type = code_element["return_value_type"]
            return_value_name = "<R>"
            short_description = code_element["description"]

            return_value_node_id = self.code_element_kg_builder.add_base_value_entity_node(value_type=return_value_type,
                                                                                           value_name=return_value_name,
                                                                                           short_description=short_description,
                                                                                           entity_category=CodeEntityCategory.CATEGORY_RETURN_VALUE)
            old_id_to_new_node_id_map[return_value_id] = return_value_node_id

        for r in relation_list:
            return_value_node_id = old_id_to_new_node_id_map[r["type_return_id"]]
            method_qualified_name = self.code_element_kg_builder.format_qualified_name(r["method_qualified_name"])

            if not method_qualified_name:
                print("not __valid method name %r" % method_qualified_name)
                continue
            node_json = self.graph_data.find_one_node_by_property("qualified_name", method_qualified_name)

            if not node_json:
                print("can't find %r, creating" % method_qualified_name)
                method_node_id = self.code_element_kg_builder.add_method_node(
                    method_qualified_name=method_qualified_name)

            else:
                method_node_id = node_json[GraphData.DEFAULT_KEY_NODE_ID]

            self.graph_data.add_relation(method_node_id,
                                         CodeEntityRelationCategory.to_str(
                                             CodeEntityRelationCategory.RELATION_CATEGORY_HAS_RETURN_VALUE),
                                         return_value_node_id)

        self.graph_data.print_graph_info()

        print("end import return value entity json")

    def import_thrown_exceptions(self, entity_json_path, entity_relation_json_path):
        print("start import thrown exceptions entity")
        print(self.graph_data)
        self.graph_data.print_label_count()

        with open(entity_json_path, "r", encoding='UTF-8') as f:
            code_list = json.load(f)
            record_num = len(code_list)
            print("load json complete size=%d" % record_num)

        with open(entity_relation_json_path, "r", encoding='UTF-8') as f:
            relation_list = json.load(f)
            record_num = len(relation_list)
            print("load json complete entity relation size=%d" % record_num)

        old_id_to_new_node_id_map = {}

        for index, code_element in enumerate(code_list):
            thrown_exception_id = code_element["id"]
            exception_type = code_element["exception_type"]
            exception_name = "<E>"
            short_description = code_element["description"]

            exception_condition_node_id = self.code_element_kg_builder.add_base_value_entity_node(
                value_type=exception_type,
                value_name=exception_name,
                short_description=short_description,
                entity_category=CodeEntityCategory.CATEGORY_EXCEPTION_CONDITION)

            old_id_to_new_node_id_map[thrown_exception_id] = exception_condition_node_id

        for r in relation_list:
            exception_condition_node_id = old_id_to_new_node_id_map[r["code_exception_id"]]
            method_qualified_name = self.code_element_kg_builder.format_qualified_name(r["method_qualified_name"])

            if not method_qualified_name:
                print("not __valid method name %r" % method_qualified_name)
                continue
            node_json = self.graph_data.find_one_node_by_property("qualified_name", method_qualified_name)

            if not node_json:
                print("can't find %r, creating" % method_qualified_name)
                method_node_id = self.code_element_kg_builder.add_method_node(
                    method_qualified_name=method_qualified_name)

            else:
                method_node_id = node_json[GraphData.DEFAULT_KEY_NODE_ID]

            self.graph_data.add_relation(method_node_id,
                                         CodeEntityRelationCategory.to_str(
                                             CodeEntityRelationCategory.RELATION_CATEGORY_HAS_EXCEPTION_CONDITION),
                                         exception_condition_node_id)

        self.graph_data.print_graph_info()

        print("end import thrown exceptions entity json")

    def infer_extra_relation(self):
        self.code_element_kg_builder.build_belong_to_relation()
        self.code_element_kg_builder.build_abstract_overloading_relation()
        # self.code_element_kg_builder.build_value_subclass_relation()
        self.code_element_kg_builder.build_belong_to_relation()
        self.code_element_kg_builder.build_override_relation()

    def add_source_label(self, source_label):
        self.code_element_kg_builder.add_source_label(source_label)

    def build_aliases(self):
        self.code_element_kg_builder.build_aliases_for_code_element()

    def save(self, graph_data_path):
        self.graph_data.save(graph_data_path)

    def save_as_simple_graph(self, output_path):
        graph_data = copy.deepcopy(self.graph_data)
        for node_id in graph_data.get_node_ids():
            node_json = graph_data.get_node_info_dict(node_id=node_id)

            properties = node_json[GraphData.DEFAULT_KEY_NODE_PROPERTIES]
            if "code" in properties:
                properties.pop("code")
        graph_data.save(output_path)

    def build_method_code_use_constant_field_relation(self):
        collection = self.export_code_document_collection()
        self.code_element_kg_builder.build_use_jdk_constant_field_relation_from_code_doc(collection)

    def export_code_document_collection(self, code_doc_collection_path=None):
        collection = self.code_element_kg_builder.export_code_document_collection(code_doc_collection_path)
        return collection
