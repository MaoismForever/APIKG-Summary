import json
import pickle
import sys

from sekg.ir.models.avg_w2v import AVGW2VFLModel

sys.path.append('/home/fdse/lvgang/APIKGSummaryV1')
from pathlib import Path

from sekg.constant.constant import DomainConstant, WikiDataConstance
from sekg.graph.exporter.graph_data import GraphData
from sekg.ir.doc.wrapper import PreprocessMultiFieldDocumentCollection, MultiFieldDocumentCollection
from sekg.ir.preprocessor.code_text import CodeDocPreprocessor
from sekg.model.word2vec.tune_word2vec import TunedWord2VecTrainer
from sekg.util.annotation import catch_exception

from doc.doc_builder import GraphNodeDocumentBuilder
from graph.builder.version.domain import DomainKGFusion
from graph.builder.version.generic import GenericKGFusion
from graph.builder.version.skeleton import SkeletonKGBuilder
from script.build_graph_data.reduce_domain_term import ReduceDomainTerm
from util.data_util import EntityReader


class CodeGraphBuilder:
    def __init__(self, ):
        pass

    @catch_exception
    def build_doc(self, graph_data_path, output_doc_collection_path=None):
        graph_data_instance = GraphData.load(str(graph_data_path))
        builder = GraphNodeDocumentBuilder(graph_data=graph_data_instance)
        return builder.build_doc_for_kg(output_doc_collection_path)

    @catch_exception
    def build_pre_doc(self, input_doc_collection_path, output_pre_doc_collection_path, preprocessor=None):

        if preprocessor == None:
            preprocessor = CodeDocPreprocessor()

        print("stat preprocess doc - for %s %r " % (input_doc_collection_path, preprocessor))
        doc_collection: MultiFieldDocumentCollection = MultiFieldDocumentCollection.load(input_doc_collection_path)
        precess_doc_collection = PreprocessMultiFieldDocumentCollection.create_from_doc_collection(
            preprocessor=preprocessor, doc_collection=doc_collection)

        precess_doc_collection.save(output_pre_doc_collection_path)
        print("end preprocess doc - %r %r " % (output_pre_doc_collection_path, preprocessor))

    @catch_exception
    def train_tune_word_embedding(self, pretained_w2v_path,
                                  tuned_word_embedding_save_path,
                                  preprocess_doc_collection: PreprocessMultiFieldDocumentCollection or Path or str = None
                                  ):

        trainer = TunedWord2VecTrainer()
        if preprocess_doc_collection == None:
            raise Exception("the preprocess_doc_collection or a path to preprocess doc_collection must be given")

        if type(preprocess_doc_collection) == str:
            preprocess_doc_collection: PreprocessMultiFieldDocumentCollection = PreprocessMultiFieldDocumentCollection.load(
                preprocess_doc_collection)

        if isinstance(preprocess_doc_collection, Path):
            preprocess_doc_collection: PreprocessMultiFieldDocumentCollection = PreprocessMultiFieldDocumentCollection.load(
                str(preprocess_doc_collection))

        if isinstance(preprocess_doc_collection, PreprocessMultiFieldDocumentCollection):
            pass

        corpus = []
        preprocess_multi_field_doc_list = preprocess_doc_collection.get_all_preprocess_document_list()
        for docno, multi_field_doc in enumerate(preprocess_multi_field_doc_list):
            corpus.append(multi_field_doc.get_document_text_words())

        print("Start training embedding...")

        w2v = trainer.tune(corpus=corpus, pretrain_w2v_path=pretained_w2v_path, pretrain_binary=True, window=5)
        w2v.wv.save(tuned_word_embedding_save_path)

        return w2v.wv

    @catch_exception
    def build_v1_graph(self, pro_name, code_analysis_data_dir, graph_data_output_dir, code_doc_collection_path=None):
        print("start build v1 graph for %s" % pro_name)
        skeleton_builder = SkeletonKGBuilder()

        base_dir = Path(code_analysis_data_dir)
        graph_data_output_dir = Path(graph_data_output_dir)
        skeleton_builder.import_primary_type()
        skeleton_builder.import_normal_entity_json(str(base_dir / "entities.json"))
        skeleton_builder.import_parameter_entity(str(base_dir / "parameter.json"),
                                                 str(base_dir / "parameter_relation.json"))
        skeleton_builder.import_field_entity(str(base_dir / "field_entities.json"),
                                             str(base_dir / "field_relation.json"))
        skeleton_builder.import_return_value_entity(str(base_dir / "return_types.json"),
                                                    str(base_dir / "return_type_relation.json"))
        skeleton_builder.import_thrown_exceptions(str(base_dir / "exceptions.json"),
                                                  str(base_dir / "exception_relation.json"))
        skeleton_builder.import_method_local_variable_entity(str(base_dir / "method_var_list.json"))
        skeleton_builder.import_normal_entity_relation_json(str(base_dir / "relations.json"))

        skeleton_builder.infer_extra_relation()
        skeleton_builder.build_aliases()
        skeleton_builder.build_method_code_use_constant_field_relation()
        skeleton_builder.add_source_label(pro_name)

        skeleton_builder.save(str(graph_data_output_dir / (pro_name + ".v1.full.graph")))
        skeleton_builder.save_as_simple_graph(str(graph_data_output_dir / (pro_name + ".v1.graph")))

        skeleton_builder.export_code_document_collection(code_doc_collection_path)

    @catch_exception
    def build_v2_graph(self, pro_name, input_graph_data_path, output_graph_data_path, domain_concept_output_dir):
        print("start adding domain knowledge for %s" % pro_name)

        builder = DomainKGFusion()

        builder.init_graph_data(input_graph_data_path)
        domain_dir = Path(domain_concept_output_dir)

        terms, operations, relations, linkages, aliases = builder.extract_term_and_relation(
            str(domain_dir / "terms.txt"),
            str(domain_dir / "operations.txt"),
            str(domain_dir / "relations.json"),
            str(domain_dir / "linkages.json"),
            not_fused_term_save_path=str(domain_dir / "not_fused_terms.txt"),
            term_aliases_save_path=str(domain_dir / "aliases.json"),
        )

        builder.fuse(terms, operations, relations, linkages, aliases)

        builder.build_aliases_for_domain_term_and_operations(str(domain_dir / "final_aliases.json"))
        builder.graph_data.add_label_to_all(pro_name)
        builder.save(output_graph_data_path)

        print("end adding domain knowledge for %s" % pro_name)

    @catch_exception
    def build_v2_1_graph_from_cache(self, pro_name, input_graph_data_path, output_graph_data_path,
                                    domain_concept_output_dir, pre_doc_collection_out_path):
        print("start adding domain knowledge for %s" % pro_name)

        builder = DomainKGFusion()

        builder.init_graph_data(input_graph_data_path)
        domain_dir = Path(domain_concept_output_dir)
        v2_1_graph_data = builder.delete_islocated_nodes_by_label(DomainConstant.LABEL_DOMAIN_TERM)

        term_save_path = str(domain_dir / "terms.txt")
        operation_save_path = str(domain_dir / "operations.txt")
        term_relation_save_path = str(domain_dir / "relations.json")
        linkage_save_path = str(domain_dir / "linkages.json")
        aliase_save_path = str(domain_dir / "aliases.json")

        reduce = ReduceDomainTerm(term_save_path, operation_save_path, term_relation_save_path, linkage_save_path,
                                  aliase_save_path, pre_doc_collection_out_path)
        # delete_based_on_name = reduce.delete_based_on_name()
        # v2_1_graph_data = builder.delete_nodes_and_relations(delete_based_on_name)
        # delete_based_on_aliase_tf = reduce.delete_based_on_aliase_tf()
        # v2_1_graph_data = builder.delete_nodes_and_relations(delete_based_on_aliase_tf)

        delete_based_on_name_length = reduce.delete_based_on_name_length()
        v2_1_graph_data = builder.delete_nodes_and_relations(delete_based_on_name_length)

        v2_1_graph_data.save(output_graph_data_path)

    @catch_exception
    def build_v2_graph_from_cache(self, pro_name, input_graph_data_path, output_graph_data_path,
                                  domain_concept_output_dir):
        print("start adding domain knowledge for %s" % pro_name)

        builder = DomainKGFusion()

        builder.init_graph_data(input_graph_data_path)
        domain_dir = Path(domain_concept_output_dir)

        term_save_path = str(domain_dir / "terms.txt")
        operation_save_path = str(domain_dir / "operations.txt")
        term_relation_save_path = str(domain_dir / "relations.json")
        linkage_save_path = str(domain_dir / "linkages.json")

        term_aliases_save_path = str(domain_dir / "aliases.json"),

        aliases = EntityReader.read_json_data(term_aliases_save_path)

        terms = EntityReader.read_line_data(term_save_path)
        operations = EntityReader.read_line_data(operation_save_path)

        relations = EntityReader.read_json_data(term_relation_save_path)
        linkages = EntityReader.read_json_data(linkage_save_path)

        builder.fuse(terms, operations, relations, linkages, aliases)
        builder.graph_data.add_label_to_all(pro_name)
        builder.save(output_graph_data_path)

        print("end adding domain knowledge for %s" % pro_name)

    @catch_exception
    def cache_wikidata_and_title_search_for_v3(self, pro_name, terms,
                                               generic_title_search_cache_path,
                                               generic_wikidata_item_cache_path,
                                               project_title_search_cache_path,
                                               project_wikidata_item_cache_path):
        fusion = GenericKGFusion()

        print("start cache wikidata search and item for %r" % pro_name)

        fusion.init_wd_from_cache(title_save_path=generic_title_search_cache_path,
                                  item_save_path=generic_wikidata_item_cache_path)

        fusion.init_wd_from_cache(title_save_path=project_title_search_cache_path,
                                  item_save_path=project_wikidata_item_cache_path)

        fusion.fetch_wikidata_by_name_and_cache_neibours(terms,
                                                         title_save_path=project_title_search_cache_path,
                                                         item_save_path=project_wikidata_item_cache_path)

        fusion.export_wd_cache(title_save_path=generic_title_search_cache_path,
                               item_save_path=generic_wikidata_item_cache_path)

        print("end cache wikidata search and item for %r" % pro_name)


    def build_v3_graph_from_cache_simple(self, pro_name,
                                         input_graph_data_path,
                                         word2vec_model_path,
                                         output_graph_data_path,
                                         generic_title_search_cache_path,
                                         generic_wikidata_item_cache_path,
                                         fusion_temp_result_dir,
                                         wikipedia_context_path,
                                         ):
        print("start adding wikidata knowledge for %s" % pro_name)

        fusion = GenericKGFusion()
        fusion.add_all_wiki_nodes()

        builder = GraphNodeDocumentBuilder(graph_data=fusion.graph_data)
        doc_collection = builder.build_doc_for_kg()

        preprocess_doc_collection = PreprocessMultiFieldDocumentCollection.create_from_doc_collection(
            preprocessor=CodeDocPreprocessor(), doc_collection=doc_collection)

        AVGW2VFLModel.train(model_dir_path=word2vec_model_path,
                            doc_collection=preprocess_doc_collection)

        fusion.init_graph_data(input_graph_data_path)
        fusion.load_w2v_model(word2vec_model_path)

        fusion.init_wd_from_cache(title_save_path=generic_title_search_cache_path,
                                  item_save_path=generic_wikidata_item_cache_path)
        fusion.init_wikipedia_contex(wikipedia_context_path=wikipedia_context_path)

        record = fusion.simple_fuse()

        fusion_temp_result_dir = Path(fusion_temp_result_dir)
        with Path(str(fusion_temp_result_dir / "record.json")).open("w", encoding="utf-8") as f:
            json.dump(record, f, indent=4)

        # fusion.graph_data.add_label_to_all(pro_name)
        fusion.save(output_graph_data_path)
        print("end adding wikidata knowledge for %s" % pro_name)

        print("model w2v model for  new graph")
        builder = GraphNodeDocumentBuilder(graph_data=fusion.graph_data)
        doc_collection = builder.build_doc_for_kg()

        preprocess_doc_collection = PreprocessMultiFieldDocumentCollection.create_from_doc_collection(
            preprocessor=CodeDocPreprocessor(), doc_collection=doc_collection)

        AVGW2VFLModel.train(model_dir_path=word2vec_model_path,
                            doc_collection=preprocess_doc_collection)
        return fusion.graph_data
