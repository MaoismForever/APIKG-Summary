class SentenceConstant:
    LABEL_SENTENCE = "sentence"
    PRIMARY_PROPERTY_NAME = "sentence_name"


class ConceptConstant:
    LABEL_CONCEPT = "concept"
    PRIMARY_PROPERTY_NAME = "concept_name"


class FeatureConstant:
    LABEL_FEATURE = "characteristic"
    PRIMARY_PROPERTY_NAME = "characteristic_name"


class RelationNameConstant:
    Interface_2_Feature = "corresponding characteristic"
    API_has_Feature_Relation = "has characteristic"
    Antonyms_Feature_Relation = "antonyms"
    Synonyms_Feature_Relation = "synonyms"
    Sentence_2_API = "describe"
    Ontology_IS_A_Relation = "is a"
    Ontology_Derive_Relation = "part of"
    Ontology_Consist_Of_Relation = "consist of"
    Ontology_Parallel_Relation = "parallel"
    Feature_Def_Sentence = "characteristic explanation"
    Domain_Def_Sentence = "category explanation"
    API_REPRESENT = "represent"



class APIRelationConstant:
    API_EXTENDS_API = "extends"
    API_IMPLEMENT_API = "implements"
    API_SUBCLASS_API = "subclass"
