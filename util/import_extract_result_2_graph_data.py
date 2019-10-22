from util.constant import SentenceConstant, ConceptConstant, FeatureConstant
from sekg.constant.constant import DomainConstant, CodeConstant
from sekg.util.annotation import catch_exception



class ExtractResultImport:
    def __init__(self, graph_data, new_graph_data_path, added_in_version):
        self.graph_data = graph_data
        self.sentence_info_label = {"entity", SentenceConstant.LABEL_SENTENCE}
        self.concept_info_label = {"entity", ConceptConstant.LABEL_CONCEPT}
        self.feature_info_label = {"entity", FeatureConstant.LABEL_FEATURE}
        # 原来定义的ontology
        self.domain_info_label = {"entity", DomainConstant.LABEL_DOMAIN_TERM}
        self.new_graph_data_path = new_graph_data_path
        self.added_in_version = added_in_version

    @catch_exception
    def add_feature_with_name(self, api_qualified_name, feature_name,
                              feature_alias_list, relation_name="has feature"):
        """
        添加形如'javax.swing.JToggleButton', 'has feature', 'serializable'
        :param feature_alias_list:
        :param feature_name:
        :param api_qualified_name:
        :param relation_name:关系名
        :return:
        """
        node_properties = {
            "added_in_version": self.added_in_version,
            FeatureConstant.PRIMARY_PROPERTY_NAME: feature_name,
            "alias": feature_alias_list
        }
        feature_node_id = self.graph_data.add_node(self.feature_info_label, node_properties,
                                                   primary_property_name=FeatureConstant.PRIMARY_PROPERTY_NAME)
        # find API
        api_node = self.graph_data.find_one_node_by_property(property_name=CodeConstant.QUALIFIED_NAME,
                                                             property_value=api_qualified_name)
        if api_node is None:
            print("the api is no exist!")
            return
        self.graph_data.add_relation(startId=api_node["id"],
                                     endId=feature_node_id,
                                     relationType=relation_name)

    @catch_exception
    def add_feature_with_id(self, api_id, feature_name, relation_name="has feature"):
        """
        使用api id添加feature关系
        添加形如 112023, 'has feature', 'first'
        :param relation_name:
        :param api_id:
        :param feature_name:
        :return:
        """
        node_properties = {"added_in_version": self.added_in_version,
                           FeatureConstant.PRIMARY_PROPERTY_NAME: feature_name}
        feature_node_id = self.graph_data.add_node(self.feature_info_label, node_properties,
                                                   primary_property_name=FeatureConstant.PRIMARY_PROPERTY_NAME)

        self.graph_data.add_relation(startId=int(api_id),
                                     endId=feature_node_id,
                                     relationType=relation_name)

    @catch_exception
    def add_ontology_relation(self, start_name, start_name_alias, end_name, end_name_alias, relation_name="is a"):
        """
        根据名字创建关系，如果实体不存在，创建实体
        :param start_name_alias:
        :param end_name_alias:
        :param start_name:
        :param end_name:
        :param relation_name: "is a" and "derive"
        :return:
        """
        start_node_is_api = False
        start_node = self.graph_data.find_one_node_by_property(property_name=CodeConstant.QUALIFIED_NAME,
                                                               property_value=start_name)

        if start_node is not None and 'labels' in start_node:
            start_id = start_node["id"]
            if "code_element" in start_node['labels']:
                start_node_is_api = True
        else:
            start_node_properties = {
                "added_in_version": self.added_in_version,
                DomainConstant.PRIMARY_PROPERTY_NAME: start_name,
                "alias": start_name_alias
            }
            start_id = self.graph_data.add_node(self.domain_info_label, start_node_properties,
                                                primary_property_name=DomainConstant.PRIMARY_PROPERTY_NAME)

        end_node_properties = {
            "added_in_version": self.added_in_version,
            DomainConstant.PRIMARY_PROPERTY_NAME: end_name,
            "alias": end_name_alias
        }
        end_id = self.graph_data.add_node(self.domain_info_label, end_node_properties,
                                          primary_property_name=DomainConstant.PRIMARY_PROPERTY_NAME)

        self.graph_data.add_relation(startId=start_id,
                                     endId=end_id,
                                     relationType=relation_name)

    @catch_exception
    def add_sentence_relation(self, sentence, api, sentence_type, relation_name="has sentence"):
        """
        :param relation_name:关系名
        :param sentence: 句子
        :param api: 从句子中抽取出来的API
        :return:
        """
        node_properties = {"added_in_version": self.added_in_version,
                           SentenceConstant.PRIMARY_PROPERTY_NAME: sentence, "type": sentence_type}
        sentence_node_id = self.graph_data.add_node(self.sentence_info_label, node_properties,
                                                    primary_property_name=SentenceConstant.PRIMARY_PROPERTY_NAME)

        # a = self.graph_data.find_one_node_by_property(SentenceConstant.PRIMARY_PROPERTY_NAME, sentence)

        self.graph_data.add_relation(startId=int(api),
                                     endId=sentence_node_id,
                                     relationType=relation_name)
        return sentence_node_id

    @catch_exception
    def add_concept_relation(self, concept, sentence_api, relation_name="mention"):
        """
        :param relation_name:关系名
        :param concept: 概念
        :param sentence_api: 句子的API
        :return:
        """
        node_properties = {"added_in_version": self.added_in_version,
                           ConceptConstant.PRIMARY_PROPERTY_NAME: concept}

        concept_node_id = self.graph_data.find_one_node_by_property(ConceptConstant.LABEL_CONCEPT, concept)
        if concept_node_id:
            pass
        else:
            concept_node_id = self.graph_data.add_node(self.concept_info_label, node_properties,
                                                       primary_property_name=ConceptConstant.PRIMARY_PROPERTY_NAME)

        self.graph_data.add_relation(startId=int(sentence_api),
                                     endId=concept_node_id,
                                     relationType=relation_name)
        return concept_node_id

    @catch_exception
    def add_antonyms_feature_relation(self, start_feature, end_feature, relation_name="antonyms"):
        """
        :param start_feature:
        :param end_feature:
        :param relation_name:
        :return:
        """
        start_node = self.graph_data.find_one_node_by_property(property_name=FeatureConstant.PRIMARY_PROPERTY_NAME,
                                                               property_value=start_feature)
        end_node = self.graph_data.find_one_node_by_property(property_name=FeatureConstant.PRIMARY_PROPERTY_NAME,
                                                             property_value=end_feature)
        # 必须已经存在feature
        if start_node is None or end_node is None:
            return None
        self.graph_data.add_relation(startId=start_node["id"],
                                     endId=end_node["id"],
                                     relationType=relation_name)

        self.graph_data.add_relation(startId=end_node["id"], endId=start_node["id"], relationType=relation_name)

    def save_new_graph_data(self):
        """
        保存新的graph data
        :return:
        """
        self.graph_data.save(self.new_graph_data_path)
