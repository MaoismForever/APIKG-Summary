import pickle

from sekg.graph.creator import NodeBuilder
from sekg.graph.exporter.graph_data import GraphData

from db.api_model import APIEntity, APIRelation
from definitions import MYSQL_FACTORY
from sekg.constant.code import CodeEntityCategory, CodeEntityRelationCategory
from sekg.graph.builder.code_kg_builder import CodeElementGraphDataBuilder
from util.path_util import PathUtil


class JDKKGBuilder:
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
            self.add_primary_type(item["name"], **code_element)

        print(self.graph_data)
        a = self.graph_data
        self.graph_data.print_label_count()

    def add_primary_type(self, primary_type_name, **properties):
        properties["qualified_name"] = primary_type_name

        cate_labels = CodeEntityCategory.to_str_list(CodeEntityCategory.CATEGORY_PRIMARY_TYPE)
        builder = NodeBuilder()
        builder = builder.add_property(**properties).add_entity_label().add_labels("code_element", *cate_labels)
        node_id = self.graph_data.add_node(
            node_id=GraphData.UNASSIGNED_NODE_ID,
            node_labels=builder.get_labels(),
            node_properties=builder.get_properties(),
            primary_property_name="qualified_name")
        return node_id

    def build_aliases(self):
        self.code_element_kg_builder.build_aliases_for_code_element()

    def infer_extra_relation(self):
        self.code_element_kg_builder.build_belong_to_relation()
        self.code_element_kg_builder.build_abstract_overloading_relation()
        # self.code_element_kg_builder.build_value_subclass_relation()
        self.code_element_kg_builder.build_belong_to_relation()
        self.code_element_kg_builder.build_override_relation()

    def save(self, graph_data_path):
        self.graph_data.save(graph_data_path)

    def import_normal_entity(self, api_entity_json):

        format_qualified_name = self.code_element_kg_builder.format_qualified_name(api_entity_json["qualified_name"])

        if not format_qualified_name:
            return
        api_entity_json.pop("qualified_name")
        node_id = self.code_element_kg_builder.add_normal_code_element_entity(format_qualified_name,
                                                                              api_entity_json["api_type"],
                                                                              **api_entity_json)
        return node_id

    def import_parameter_entity(self, api_entity_json):
        extra_properties = {}

        qualified_name = api_entity_json["qualified_name"]
        short_description = api_entity_json["short_description"]

        value_type = qualified_name.split(" ")[0].strip()
        value_name = qualified_name.split(" ")[1].strip()
        ## todo: add all class node first, in case adding the parameter node without type info
        node_id = self.code_element_kg_builder.add_base_value_entity_node(value_type=value_type, value_name=value_name,
                                                                          short_description=short_description,
                                                                          entity_category=CodeEntityCategory.CATEGORY_PARAMETER,
                                                                          **extra_properties)

        if node_id == GraphData.UNASSIGNED_NODE_ID:
            print("fail to add parameter node %r" % (api_entity_json))

        return node_id

    def import_return_value_entity(self, api_entity_json):
        extra_properties = {}

        qualified_name = api_entity_json["qualified_name"]
        short_description = api_entity_json["short_description"]

        value_type = qualified_name.split(" ")[0].strip()
        ## todo: add all class node first, in case adding the parameter node without type info
        node_id = self.code_element_kg_builder.add_base_value_entity_node(value_type=value_type, value_name="<R>",
                                                                          short_description=short_description,
                                                                          entity_category=CodeEntityCategory.CATEGORY_RETURN_VALUE,
                                                                          **extra_properties)

        if node_id == GraphData.UNASSIGNED_NODE_ID:
            print("fail to add parameter node %r" % (api_entity_json))

        return node_id

    def import_exception_condition_entity(self, api_entity_json):
        extra_properties = {}

        qualified_name = api_entity_json["qualified_name"]
        short_description = api_entity_json["short_description"]

        value_type = qualified_name.split(" ")[0].strip()
        ## todo: add all class node first, in case adding the parameter node without type info
        node_id = self.code_element_kg_builder.add_base_value_entity_node(value_type=value_type, value_name="<E>",
                                                                          short_description=short_description,
                                                                          entity_category=CodeEntityCategory.CATEGORY_RETURN_VALUE,
                                                                          **extra_properties)

        if node_id == GraphData.UNASSIGNED_NODE_ID:
            print("fail to add parameter node %r" % (api_entity_json))

        return node_id

    def import_construct_method_entity(self, api_entity_json):

        format_qualified_name = self.code_element_kg_builder.format_qualified_name(api_entity_json["qualified_name"])

        method_name = self.code_element_kg_builder.parse_construct_to_javaparser_style(format_qualified_name)

        if not method_name:
            return GraphData.UNASSIGNED_NODE_ID

        api_entity_json.pop("qualified_name")
        node_id = self.code_element_kg_builder.add_normal_code_element_entity(method_name,
                                                                              api_entity_json["api_type"],
                                                                              **api_entity_json)

        return node_id

    def import_qualified_field_entity(self, api_entity_json):
        # print("import_qualified_field_entity %r %r" % (api_entity_json["qualified_name"], api_entity_json))

        qualified_name = self.code_element_kg_builder.format_qualified_name(api_entity_json["qualified_name"])
        if not qualified_name:
            print("import_qualified_field_entity %r %r" % (api_entity_json["qualified_name"], api_entity_json))
            return GraphData.UNASSIGNED_NODE_ID

        api_entity_json.pop("qualified_name")
        api_entity_json.pop("api_type")

        node_id = self.code_element_kg_builder.add_normal_code_element_entity(qualified_name,
                                                                              CodeEntityCategory.CATEGORY_FIELD_OF_CLASS,
                                                                              **api_entity_json)

        return node_id

    def import_qualified_enum_constants_entity(self, api_entity_json):
        # print("import_qualified_field_entity %r %r" % (api_entity_json["qualified_name"], api_entity_json))

        qualified_name = self.code_element_kg_builder.format_qualified_name(api_entity_json["qualified_name"])
        if not qualified_name:
            print("import_qualified_field_entity %r %r" % (api_entity_json["qualified_name"], api_entity_json))
            return GraphData.UNASSIGNED_NODE_ID

        api_entity_json.pop("qualified_name")
        api_entity_json.pop("api_type")

        node_id = self.code_element_kg_builder.add_normal_code_element_entity(qualified_name,
                                                                              CodeEntityCategory.CATEGORY_ENUM_CONSTANTS,
                                                                              **api_entity_json)

        return node_id

    def import_jdk_from_api_table(self, session):
        print("start import_jdk_from_api_table ")
        # api_entity_list = session.query(APIEntity).filter(APIEntity.id > 85000).limit(1000).all()
        api_entity_list = session.query(APIEntity).all()

        api_id_to_node_id_map = {}
        for entity_info_row in api_entity_list:

            api_entity_json = dict(entity_info_row.__dict__)
            api_entity_json.pop('_sa_instance_state', None)
            api_id = api_entity_json["id"]
            qualified_name = api_entity_json["qualified_name"]
            api_type = api_entity_json["api_type"]

            if self.is_jdk_api(qualified_name) == False:
                if self.is_android_support(qualified_name):
                    continue
                if self.is_android_core_api(qualified_name):
                    continue

                # if self.is_android_core_api(qualified_name) == False:
                print("Not jdk %d %s %r " % (api_id, qualified_name, CodeEntityCategory.to_str(api_type)))
                continue

            normal_entity_types = {
                CodeEntityCategory.CATEGORY_CLASS,
                CodeEntityCategory.CATEGORY_PACKAGE,
                CodeEntityCategory.CATEGORY_METHOD,
                CodeEntityCategory.CATEGORY_INTERFACE,
                CodeEntityCategory.CATEGORY_EXCEPTION_CLASS,
                CodeEntityCategory.CATEGORY_ENUM_CLASS,
                CodeEntityCategory.CATEGORY_ERROR_CLASS,
                CodeEntityCategory.CATEGORY_ANNOTATION_CLASS,

            }
            node_id = GraphData.UNASSIGNED_NODE_ID
            if api_type in normal_entity_types:
                node_id = self.import_normal_entity(api_entity_json)
            if api_type == CodeEntityCategory.CATEGORY_CONSTRUCT_METHOD:
                node_id = self.import_construct_method_entity(api_entity_json)

            if api_type == CodeEntityCategory.CATEGORY_FIELD_OF_CLASS:
                node_id = self.import_qualified_field_entity(api_entity_json)

            if api_type == CodeEntityCategory.CATEGORY_ENUM_CONSTANTS:
                node_id = self.import_qualified_enum_constants_entity(api_entity_json)
            if api_type == CodeEntityCategory.CATEGORY_PRIMARY_TYPE:
                node_id = self.add_primary_type(primary_type_name=qualified_name, **api_entity_json)

            if api_type == CodeEntityCategory.CATEGORY_PARAMETER:
                node_id = self.import_parameter_entity(api_entity_json)
            if api_type == CodeEntityCategory.CATEGORY_RETURN_VALUE:
                node_id = self.import_return_value_entity(api_entity_json)
            if api_type == CodeEntityCategory.CATEGORY_EXCEPTION_CONDITION:
                node_id = self.import_exception_condition_entity(api_entity_json)
            if node_id == GraphData.UNASSIGNED_NODE_ID:
                print("Adding fail %d %s %r " % (api_id, qualified_name, CodeEntityCategory.to_str(api_type)))
                continue
            api_id_to_node_id_map[api_id] = node_id

        self.graph_data.print_graph_info()
        print("end import_jdk_from_api_table ")

        return api_id_to_node_id_map

    def import_android_from_api_table(self, session):
        print("start import android api from jdk table")
        # api_entity_list = session.query(APIEntity).filter(APIEntity.id > 85000).limit(1000).all()
        api_entity_list = session.query(APIEntity).all()

        api_id_to_node_id_map = {}
        for entity_info_row in api_entity_list:

            api_entity_json = dict(entity_info_row.__dict__)
            api_entity_json.pop('_sa_instance_state', None)
            api_id = api_entity_json["id"]
            qualified_name = api_entity_json["qualified_name"]
            api_type = api_entity_json["api_type"]

            if self.is_android_support(qualified_name):
                continue

            if self.is_jdk_api(qualified_name) == False and self.is_android_core_api(qualified_name) == False:
                # if self.is_android_core_api(qualified_name) == False:
                print(
                    "Not android or JDK API %d %s %r " % (api_id, qualified_name, CodeEntityCategory.to_str(api_type)))
                continue
            normal_entity_types = {
                CodeEntityCategory.CATEGORY_CLASS,
                CodeEntityCategory.CATEGORY_PACKAGE,
                CodeEntityCategory.CATEGORY_METHOD,
                CodeEntityCategory.CATEGORY_INTERFACE,
                CodeEntityCategory.CATEGORY_EXCEPTION_CLASS,
                CodeEntityCategory.CATEGORY_ENUM_CLASS,
                CodeEntityCategory.CATEGORY_ERROR_CLASS,
                CodeEntityCategory.CATEGORY_ANNOTATION_CLASS,

            }
            node_id = GraphData.UNASSIGNED_NODE_ID
            if api_type in normal_entity_types:
                node_id = self.import_normal_entity(api_entity_json)
            if api_type == CodeEntityCategory.CATEGORY_CONSTRUCT_METHOD:
                node_id = self.import_construct_method_entity(api_entity_json)

            if api_type == CodeEntityCategory.CATEGORY_FIELD_OF_CLASS:
                node_id = self.import_qualified_field_entity(api_entity_json)

            if api_type == CodeEntityCategory.CATEGORY_ENUM_CONSTANTS:
                node_id = self.import_qualified_enum_constants_entity(api_entity_json)
            if api_type == CodeEntityCategory.CATEGORY_PRIMARY_TYPE:
                node_id = self.add_primary_type(primary_type_name=qualified_name, **api_entity_json)

            if api_type == CodeEntityCategory.CATEGORY_PARAMETER:
                node_id = self.import_parameter_entity(api_entity_json)
            if api_type == CodeEntityCategory.CATEGORY_RETURN_VALUE:
                node_id = self.import_return_value_entity(api_entity_json)
            if api_type == CodeEntityCategory.CATEGORY_EXCEPTION_CONDITION:
                node_id = self.import_exception_condition_entity(api_entity_json)
            if node_id == GraphData.UNASSIGNED_NODE_ID:
                print("Adding fail %d %s %r " % (api_id, qualified_name, CodeEntityCategory.to_str(api_type)))
                continue
            api_id_to_node_id_map[api_id] = node_id

        self.graph_data.print_graph_info()
        print("end import_jdk_from_api_table ")

        return api_id_to_node_id_map

    def import_relation_from_jdk_table(self, session, api_id_to_node_id_map):
        print("start import jdk relation")
        self.graph_data.print_graph_info()

        valid_api_types = CodeEntityRelationCategory.relation_set()

        for relation_type in valid_api_types:
            relation_str = CodeEntityRelationCategory.to_str(relation_type)
            print("start import relation %s" % (relation_str))
            api_relation_list = session.query(APIRelation).filter(APIRelation.relation_type == relation_type).all()
            for relation in api_relation_list:
                if relation.start_api_id not in api_id_to_node_id_map:
                    print("start_id %d can't found its node id" % (relation.start_api_id))
                    continue
                if relation.end_api_id not in api_id_to_node_id_map:
                    print("end_id %d can't found its node id" % (relation.end_api_id))
                    continue
                self.graph_data.add_relation(startId=api_id_to_node_id_map[relation.start_api_id],
                                             endId=api_id_to_node_id_map[relation.end_api_id],
                                             relationType=relation_str)
        print("end import jdk relation")
        self.graph_data.print_graph_info()

    def is_jdk_api(self, qualified_name):
        if qualified_name.startswith("java."):
            return True
        if qualified_name.startswith("javax."):
            return True
        if qualified_name.startswith("org.w3c.dom"):
            return True
        if qualified_name.startswith("org.xml.sax"):
            return True
        if qualified_name.startswith("org.ietf"):
            return True
        if qualified_name.startswith("org.omg"):
            return True
        for primary in CodeEntityCategory.JAVA_PRIMARY_TYPE_SET:
            if qualified_name.startswith(primary):
                return True
        # the Generic type parameter,eg. T element, T[]
        if len(qualified_name.strip("[]").split(" ")[0]) == 1:
            return True

        return False

    def is_android_support(self, qualified_name):
        if qualified_name.startswith("androidx"):
            return True
        if qualified_name.startswith("android.support"):
            return True
        return False

    def is_android_core_api(self, qualified_name):

        if self.is_android_support(qualified_name):
            return False
        if qualified_name.startswith("android"):
            return True
        if qualified_name.startswith("com.android.internal.util"):
            return True
        if qualified_name.startswith("dalvik."):
            return True
        if qualified_name.startswith("junit."):
            return True
        if qualified_name.startswith("org.xmlpull"):
            return True
        if qualified_name.startswith("org.json"):
            return True
        if qualified_name.startswith("org.apache"):
            return True
        return False

    def add_source_label(self, source_label):
        self.code_element_kg_builder.add_source_label(source_label)


def build_v1_jdk():
    jdk_kg_builder = JDKKGBuilder()
    pro_name = "jdk8"
    output_graph_data_path = PathUtil.jdk_graph_data()
    session = MYSQL_FACTORY.create_mysql_session_by_server_name(server_name="89Server",
                                                                database="api_backup",
                                                                echo=False)
    jdk_kg_builder.import_primary_type()
    api_id_to_node_id_map = jdk_kg_builder.import_jdk_from_api_table(session)
    id_map_file_path = PathUtil.jdk_api_node_map()
    with open(id_map_file_path, 'wb') as id_map_file:
        pickle.dump(api_id_to_node_id_map, id_map_file)
    jdk_kg_builder.save(output_graph_data_path)
    jdk_kg_builder.init_graph_data(output_graph_data_path)
    jdk_kg_builder.import_relation_from_jdk_table(session, api_id_to_node_id_map)
    jdk_kg_builder.save(output_graph_data_path)
    jdk_kg_builder.infer_extra_relation()
    jdk_kg_builder.build_aliases()
    jdk_kg_builder.add_source_label(pro_name)
    jdk_kg_builder.save(output_graph_data_path)


if __name__ == "__main__":
    build_v1_jdk()