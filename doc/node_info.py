from sekg.graph.exporter.graph_data import NodeInfo, NodeInfoFactory
from sekg.util.code import CodeElementNameUtil

import sys

from db.api_model import APIEntity
from db.model import CodeElement
from sekg.constant.code import CodeEntityCategory
from sekg.constant.constant import DomainConstant, OperationConstance, PropertyConstant, CodeConstant, \
    WikiDataConstance


class ProjectKGNodeInfoFactory(NodeInfoFactory):

    def create_node_info(self, node_info_dict):
        labels = node_info_dict["labels"]
        node_id = node_info_dict["id"]
        properties = node_info_dict["properties"]
        return self.__create_node_info(labels, node_id, properties)

    def __create_node_info(self, labels, node_id, properties):
        if CodeConstant.LABEL_CODE_ELEMENT in labels:
            return CodeElementNodeInfo(node_id=node_id,
                                       labels=labels,
                                       properties=properties)
        if DomainConstant.LABEL_DOMAIN_TERM in labels:
            return DomainEntityNodeInfo(node_id=node_id,
                                        labels=labels,
                                        properties=properties)

        if OperationConstance.LABEL_OPERATION in labels:
            return OperationEntityNodeInfo(node_id=node_id,
                                           labels=labels,
                                           properties=properties)
        if WikiDataConstance.LABEL_WIKIDATA in labels:
            return WikidataEntityNodeInfo(node_id=node_id,
                                          labels=labels,
                                          properties=properties)
        return NodeInfo(node_id=node_id,
                        labels=labels,
                        properties=properties)


class DomainEntityNodeInfo(NodeInfo):
    DOMAIN_ENTITY_PRIVATE_PROPERTIES = {
        DomainConstant.PRIMARY_PROPERTY_NAME,
    }

    def get_main_name(self):
        return self.properties[DomainConstant.PRIMARY_PROPERTY_NAME]

    def get_all_names(self):
        name_list = [self.get_main_name(), ]
        if PropertyConstant.ALIAS in self.properties:
            name_list.extend(self.properties[PropertyConstant.ALIAS])

        if PropertyConstant.LEMMA in self.properties:
            name_list.append(self.properties[PropertyConstant.LEMMA])

        if "aliases_en" in self.properties:
            name_list.extend(self.properties["aliases_en"])

        return list(set(name_list))

    def get_all_valid_attributes(self):
        valid_attribute_pairs = []
        for property_name in self.properties.keys():
            if self.is_valid_property(property_name):
                value = self.properties[property_name]
                valid_attribute_pairs.append((property_name, value))

        return valid_attribute_pairs

    def is_valid_property(self, property_name):
        valid = super().is_valid_property(property_name=property_name)
        if not valid:
            return False

        if property_name in self.DOMAIN_ENTITY_PRIVATE_PROPERTIES:
            return False

        return True

    def __repr__(self):
        return "<DomainEntityNodeInfo id=%d labels=%r properties=%r>" % (
            self.node_id,
            self.labels,
            self.properties)


class OperationEntityNodeInfo(NodeInfo):

    def get_main_name(self):
        return self.properties[OperationConstance.PRIMARY_PROPERTY_NAME]

    def get_all_names(self):
        name_list = [self.get_main_name(), ]
        if PropertyConstant.ALIAS in self.properties:
            name_list.extend(self.properties[PropertyConstant.ALIAS])

        if PropertyConstant.LEMMA in self.properties:
            name_list.append(self.properties[PropertyConstant.LEMMA])

        return list(set(name_list))

    def get_all_valid_attributes(self):
        valid_attribute_pairs = []
        for property_name in self.properties.keys():
            if self.is_valid_property(property_name):
                value = self.properties[property_name]
                valid_attribute_pairs.append((property_name, value))

        return valid_attribute_pairs

    def is_valid_property(self, property_name):

        return True

    def __repr__(self):
        return "<OperationEntityNodeInfo id=%d labels=%r properties=%r>" % (
            self.node_id,
            self.labels,
            self.properties)


class CodeElementNodeInfo(NodeInfo):
    CODE_ELEMENT_PRIVATE_PROPERTY = [
        "api_type",
        "added_in_version",
    ]
    name_util = CodeElementNameUtil()

    def get_main_name(self):
        return self.properties["qualified_name"]

    def get_all_names(self):
        qualified_name = self.properties["qualified_name"]
        name_util = CodeElementNodeInfo.name_util
        include_parent_name = False
        if (CodeEntityCategory.to_str(CodeEntityCategory.CATEGORY_METHOD) in self.labels and CodeEntityCategory.to_str(
                CodeEntityCategory.CATEGORY_CONSTRUCT_METHOD) not in self.labels) or CodeEntityCategory.to_str(
            CodeEntityCategory.CATEGORY_ENUM_CONSTANTS) in self.labels or CodeEntityCategory.to_str(
            CodeEntityCategory.CATEGORY_FIELD_OF_CLASS) in self.labels or CodeEntityCategory.to_str(
            CodeEntityCategory.CATEGORY_BASE_OVERRIDE_METHOD) in self.labels:
            include_parent_name = True

        name_list = name_util.generate_aliases(qualified_name=qualified_name,
                                               include_simple_parent_name=include_parent_name)

        if "simple_name" in self.properties:
            name_list.append(self.properties["simple_name"])
        if "alias" in self.properties:
            name_list.extend(self.properties["alias"])
        return list(set(name_list))

    def get_all_valid_attributes(self):
        valid_attribute_pairs = []

        for property_name in self.properties.keys():
            if self.is_valid_property(property_name):
                value = self.properties[property_name]
                if not value:
                    continue
                if "_" in property_name:
                    property_name = property_name.replace("_", " ")

                valid_attribute_pairs.append((property_name, value))

        type_str = ""
        if "element_type" in self.properties.keys():
            value = self.properties["element_type"]
            type_str = CodeElement.get_simple_type_string(int(value))

        if "api_type" in self.properties.keys():
            value = self.properties["api_type"]
            type_str = APIEntity.get_simple_type_string(int(value))

        if type_str:
            valid_attribute_pairs.append(("type", type_str))

        return valid_attribute_pairs

    def is_valid_property(self, property_name):
        valid = super().is_valid_property(property_name=property_name)
        if not valid:
            return False

        if property_name in CodeElementNodeInfo.CODE_ELEMENT_PRIVATE_PROPERTY:
            return False
        return True

    def __repr__(self):
        return "<CodeElementNodeInfo id=%d labels=%r properties=%r>" % (
            self.node_id,
            self.labels,
            self.properties)


class WikidataEntityNodeInfo(NodeInfo):
    PRIVATE_PROPERTIES = {

    }

    def get_main_name(self):
        return self.properties.get(WikiDataConstance.NAME, "")

    def get_all_names(self):
        name_list = [self.get_main_name(), ]
        name_list.extend(list(self.properties.get(PropertyConstant.ALIAS, [])))
        name_list.extend(list(self.properties.get("aliases_en", [])))
        name_list = [name for name in name_list if name]
        return list(set(name_list))

    def get_all_valid_attributes(self):
        valid_attribute_pairs = []
        for property_name in self.properties.keys():
            if self.is_valid_property(property_name):
                value = self.properties[property_name]
                valid_attribute_pairs.append((property_name, value))

        return valid_attribute_pairs

    def is_valid_property(self, property_name):
        valid = super().is_valid_property(property_name=property_name)
        if not valid:
            return False

        if property_name in self.PRIVATE_PROPERTIES:
            return False

        return True

    def __repr__(self):
        return "<WikidataEntityNodeInfo id=%d labels=%r properties=%r>" % (
            self.node_id,
            self.labels,
            self.properties)
