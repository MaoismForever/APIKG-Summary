import json
import pickle
import sys

sys.path.append('/home/fdse/lvgang/APIKGSummaryV1')
from pathlib import Path

from sekg.constant.constant import DomainConstant, WikiDataConstance
from sekg.graph.exporter.graph_data import GraphData
from sekg.ir.doc.wrapper import PreprocessMultiFieldDocumentCollection, MultiFieldDocumentCollection
from sekg.ir.preprocessor.code_text import CodeDocPreprocessor
from sekg.model.word2vec.tune_word2vec import TunedWord2VecTrainer
from sekg.text.extractor.domain_entity.relation_detection import RelationType
from sekg.util.annotation import catch_exception

from doc.doc_builder import GraphNodeDocumentBuilder
from graph.builder.version.domain import DomainKGFusion
from graph.builder.version.generic import GenericKGFusion
from graph.builder.version.jdk_fusion import JDKKGFusion
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

    def build_v3_graph_from_cache(self, pro_name,
                                  input_graph_data_path,
                                  word2vec_model_path,
                                  output_graph_data_path,
                                  concept_list: list or set or str,
                                  generic_title_search_cache_path,
                                  generic_wikidata_item_cache_path,
                                  project_title_search_cache_path,
                                  project_wikidata_item_cache_path,
                                  fusion_temp_result_dir,
                                  pretrain_w2v_path,

                                  ):
        print("start adding wikidata knowledge for %s" % pro_name)

        # todo: need test
        fusion = GenericKGFusion()

        doc_collection = self.build_doc(graph_data_path=input_graph_data_path)
        preprocess_doc_collection = PreprocessMultiFieldDocumentCollection.create_from_doc_collection(
            preprocessor=CodeDocPreprocessor(), doc_collection=doc_collection)

        print("start training the tuned word2vec model %s" % (word2vec_model_path))
        self.train_tune_word_embedding(
            pretained_w2v_path=pretrain_w2v_path,
            preprocess_doc_collection=preprocess_doc_collection,
            tuned_word_embedding_save_path=word2vec_model_path,
        )

        fusion.init_graph_data(input_graph_data_path)
        fusion.load_word_embedding(word2vec_model_path)

        fusion.init_wd_from_cache(title_save_path=generic_title_search_cache_path,
                                  item_save_path=generic_wikidata_item_cache_path)

        fusion.init_wd_from_cache(title_save_path=project_title_search_cache_path,
                                  item_save_path=project_wikidata_item_cache_path)

        neighbours, record = fusion.fuse()

        fusion_temp_result_dir = Path(fusion_temp_result_dir)
        # fusion.save(PathUtil.graph_data(pro_name=pro_name, version="v2.5"))
        # todo: remove v2.5 graph builder and test?
        with Path(str(fusion_temp_result_dir / "record.json")).open("w", encoding="utf-8") as f:
            json.dump(record, f, indent=4)
        with Path(str(fusion_temp_result_dir / "neighbours.bin")).open("wb") as f:
            pickle.dump(neighbours, f)

        fusion.add_wikidata_items(neighbours)
        fusion.graph_data.add_label_to_all(pro_name)
        fusion.save(output_graph_data_path)
        print("end adding wikidata knowledge for %s" % pro_name)
        return fusion.graph_data

    def build_v3_graph_from_cache_simple(self, pro_name,
                                         input_graph_data_path,
                                         word2vec_model_path,
                                         output_graph_data_path,
                                         concept_list: list or set or str,
                                         generic_title_search_cache_path,
                                         generic_wikidata_item_cache_path,
                                         project_title_search_cache_path,
                                         project_wikidata_item_cache_path,
                                         fusion_temp_result_dir,
                                         pretrain_w2v_path,
                                         wikipedia_context_path,
                                         ):
        print("start adding wikidata knowledge for %s" % pro_name)

        fusion = GenericKGFusion()

        # doc_collection = self.build_doc(graph_data_path=input_graph_data_path)
        # preprocess_doc_collection = PreprocessMultiFieldDocumentCollection.create_from_doc_collection(
        #     preprocessor=CodeDocPreprocessor(), doc_collection=doc_collection)
        #
        # print("start training the tuned word2vec model %s" % (word2vec_model_path))
        # self.train_tune_word_embedding(
        #     pretained_w2v_path=pretrain_w2v_path,
        #     preprocess_doc_collection=preprocess_doc_collection,
        #     tuned_word_embedding_save_path=word2vec_model_path,
        # )

        fusion.init_graph_data(input_graph_data_path)
        fusion.load_w2v_model(word2vec_model_path)

        # fusion.load_word_embedding(word2vec_model_path)

        fusion.init_wd_from_cache(title_save_path=generic_title_search_cache_path,
                                  item_save_path=generic_wikidata_item_cache_path)

        # fusion.init_wd_from_cache(title_save_path=project_title_search_cache_path,
        #                           item_save_path=project_wikidata_item_cache_path)

        fusion.init_wikipedia_contex(wikipedia_context_path=wikipedia_context_path)

        neighbours, record = fusion.simple_fuse()

        fusion_temp_result_dir = Path(fusion_temp_result_dir)
        with Path(str(fusion_temp_result_dir / "record.json")).open("w", encoding="utf-8") as f:
            json.dump(record, f, indent=4)
        with Path(str(fusion_temp_result_dir / "neighbours.bin")).open("wb") as f:
            pickle.dump(neighbours, f)

        fusion.add_wikidata_items(neighbours)
        fusion.graph_data.add_label_to_all(pro_name)
        fusion.save(output_graph_data_path)
        print("end adding wikidata knowledge for %s" % pro_name)
        return fusion.graph_data

    def build_v3_graph_from_cache_with_twice_fuse(self, pro_name,
                                                  input_graph_data_path,
                                                  word2vec_model_path,
                                                  output_graph_data_path,
                                                  concept_list: list or set or str,
                                                  generic_title_search_cache_path,
                                                  generic_wikidata_item_cache_path,
                                                  project_title_search_cache_path,
                                                  project_wikidata_item_cache_path,
                                                  fusion_temp_result_dir,
                                                  pretrain_w2v_path,

                                                  ):
        print("start adding wikidata knowledge for %s" % pro_name)

        # todo: need test
        fusion = GenericKGFusion()

        doc_collection = self.build_doc(graph_data_path=input_graph_data_path)
        preprocess_doc_collection = PreprocessMultiFieldDocumentCollection.create_from_doc_collection(
            preprocessor=CodeDocPreprocessor(), doc_collection=doc_collection)

        print("start training the tuned word2vec model %s" % (word2vec_model_path))
        self.train_tune_word_embedding(
            pretained_w2v_path=pretrain_w2v_path,
            preprocess_doc_collection=preprocess_doc_collection,
            tuned_word_embedding_save_path=word2vec_model_path,
        )

        fusion.init_graph_data(input_graph_data_path)
        fusion.load_word_embedding(word2vec_model_path)

        fusion.init_wd_from_cache(title_save_path=generic_title_search_cache_path,
                                  item_save_path=generic_wikidata_item_cache_path)

        fusion.init_wd_from_cache(title_save_path=project_title_search_cache_path,
                                  item_save_path=project_wikidata_item_cache_path)

        neighbours, record = fusion.fuse()

        fusion_temp_result_dir = Path(fusion_temp_result_dir)
        # fusion.save(PathUtil.graph_data(pro_name=pro_name, version="v2.5"))
        # todo: remove v2.5 graph builder and test?
        with Path(str(fusion_temp_result_dir / "record.json")).open("w", encoding="utf-8") as f:
            json.dump(record, f, indent=4)
        with Path(str(fusion_temp_result_dir / "neighbours.bin")).open("wb") as f:
            pickle.dump(neighbours, f)

        fusion.add_wikidata_items(neighbours)
        # fusion.graph_data.add_label_to_all(pro_name)
        # fusion.save(output_graph_data_path)

        print("start second fusing.........")
        neighbours_2, record_2 = fusion.fuse()
        fusion_temp_result_dir = Path(fusion_temp_result_dir)
        with Path(str(fusion_temp_result_dir / "record_second.json")).open("w", encoding="utf-8") as f:
            json.dump(record_2, f, indent=4)
        with Path(str(fusion_temp_result_dir / "neighbours_second.bin")).open("wb") as f:
            pickle.dump(neighbours_2, f)
        fusion.add_wikidata_items(neighbours_2)

        print("start merge domain nodes fuse same wikiitem...")
        record.extend(record_2)
        count_record = {}
        for item in record:
            if item["link"]:
                item_tuple = (item["domain_id"], item["context_score"], item["topic_score"], item["score"])
                if item["wd_item_id"] not in count_record:
                    count_record[item["wd_item_id"]] = [item_tuple]
                else:
                    count_record[item["wd_item_id"]].append(item_tuple)
        for key in count_record:
            count_record[key] = sorted(count_record[key], key=lambda x: (x[1], x[2], x[3]))
            if len(count_record[key]) > 1:
                need_merge_nodes = [m[0] for m in count_record[key]]
                fusion.merge_domain_nodes_fuse_same_wiki_item(need_merge_nodes)

        fusion.graph_data.add_label_to_all(pro_name)
        fusion.graph_data.refresh_indexer()
        fusion.save(output_graph_data_path)
        print("end adding wikidata knowledge for %s" % pro_name)
        return fusion.graph_data

    def build_v3_2_graph(self, pro_name,
                         input_graph_data_path,
                         output_graph_data_path,
                         generic_wikidata_item_cache_path,
                         project_wikidata_item_cache_path,
                         fusion_temp_result_dir
                         ):
        print("start adding wikidata knowledge for %s" % pro_name)

        # todo: need test
        fusion = GenericKGFusion()

        fusion.init_graph_data(input_graph_data_path)

        fusion.init_wd_from_cache(title_save_path=None,
                                  item_save_path=generic_wikidata_item_cache_path)

        fusion.init_wd_from_cache(title_save_path=None,
                                  item_save_path=project_wikidata_item_cache_path)

        wiki_domain_same_name, wiki_domain_relation = fusion.fuse_with_prefix_and_suffix()
        fusion_temp_result_dir = Path(fusion_temp_result_dir)
        with Path(str(fusion_temp_result_dir / "wiki_domain_same_name.json")).open("w", encoding="utf-8") as f:
            json.dump(wiki_domain_same_name, f, indent=4)
        with Path(str(fusion_temp_result_dir / "wiki_domain_relation.json")).open("w", encoding="utf-8") as f:
            json.dump(wiki_domain_relation, f, indent=4)

        fusion.graph_data.add_label_to_all(pro_name)
        fusion.graph_data.refresh_indexer()
        fusion.save(output_graph_data_path)
        print("end adding wikidata knowledge for %s" % pro_name)
        return fusion.graph_data

    @catch_exception
    def build_graph_by_fuse_jdk(self, pro_name,
                                input_graph_data_path,
                                output_graph_data_path,
                                jdk_graph_data_path,
                                code_document_collection_path=None,
                                ):
        print("start build v4 graph for %s by adding JDK V3 graph" % pro_name)
        fusion = JDKKGFusion()
        input_graph_data: GraphData = GraphData.load(input_graph_data_path)
        jdk_graph_data: GraphData = GraphData.load(jdk_graph_data_path)

        fusion.fuse(input_graph_data, jdk_graph_data)

        code_document_collection = None

        if code_document_collection_path != None:
            code_document_collection: MultiFieldDocumentCollection = MultiFieldDocumentCollection.load(
                code_document_collection_path)

        if code_document_collection != None:
            fusion.build_use_jdk_constant_field_relation_from_code_doc(code_document_collection)
        fusion.graph_data.refresh_indexer()
        fusion.save(output_graph_data_path)

    @catch_exception
    def build_small_graph_based_on_v4(self, pro_name, input_graph_data_path, out_put_graph_data_path, max_hop=3,
                                      include_outs=True, include_ins=False):
        print("start build small v4 graph based on v4 for %r" % pro_name)

        v4_graph_data: GraphData = GraphData.load(input_graph_data_path)
        print(v4_graph_data)

        project_node_ids = v4_graph_data.get_node_ids_by_label(label=pro_name)
        project_node_ids = set(project_node_ids)

        current_start_node_ids = set(project_node_ids)
        next_node_ids = set([])
        print("project node num=%d" % len(project_node_ids))

        for hop in range(0, max_hop):
            for node_id in current_start_node_ids:
                if include_outs:
                    out_relation = v4_graph_data.get_all_out_relations(node_id)
                    for s, r, e in out_relation:
                        next_node_ids.add(s)
                        next_node_ids.add(e)
                if include_ins:
                    in_relation = v4_graph_data.get_all_in_relations(node_id)
                    for s, r, e in in_relation:
                        next_node_ids.add(s)
                        next_node_ids.add(e)
            current_start_node_ids = next_node_ids | current_start_node_ids
            print("when hop=%d, node num=%d" % (hop, len(current_start_node_ids)))

        small_graph = v4_graph_data.subgraph(current_start_node_ids)
        print(small_graph)
        small_graph.refresh_indexer()
        small_graph.save(out_put_graph_data_path)
        print("build complete and save to %s" % out_put_graph_data_path)

    @catch_exception
    def build_small_graph_based_on_v4_2_add_reverse_edges(self, pro_name, input_graph_data_path,
                                                          out_put_graph_data_path):
        """
        based v4.2 delete relation (class-operation, domain term-operation)
        add reverse edge for node (except wiki)
        """
        print("start build small v4 graph based on v4 for %r" % pro_name)

        v4_graph_data: GraphData = GraphData.load(input_graph_data_path)
        print(v4_graph_data)

        v4_graph_data = self.add_reverse_edge(v4_graph_data)
        v4_graph_data.save(out_put_graph_data_path)
        print("build complete and save to %s" % out_put_graph_data_path)

    @catch_exception
    def build_v3_1_graph(self, pro_name, input_graph_data_path, output_graph_data_path,
                         domain_concept_output_dir, pre_doc_collection_out_path):
        print("start adding domain knowledge for %s" % pro_name)
        builder = DomainKGFusion()
        builder.init_graph_data(input_graph_data_path)

        # domain_dir = Path(domain_concept_output_dir)
        # term_save_path = str(domain_dir / "terms.txt")
        # operation_save_path = str(domain_dir / "operations.txt")
        # term_relation_save_path = str(domain_dir / "relations.json")
        # linkage_save_path = str(domain_dir / "linkages.json")
        # aliase_save_path = str(domain_dir / "aliases.json")
        #
        # reduce = ReduceDomainTerm(term_save_path, operation_save_path, term_relation_save_path, linkage_save_path,
        #                           aliase_save_path, pre_doc_collection_out_path)
        # delete_based_on_name_length = reduce.delete_based_on_name_length()
        # v2_1_graph_data = builder.delete_nodes_and_relations(delete_based_on_name_length)

        v2_1_graph_data = builder.filter_domain_by_name_length(name_length=30, name_split_number=3)
        v2_1_graph_data = builder.delete_islocated_nodes_by_label(DomainConstant.LABEL_DOMAIN_TERM)
        v2_1_graph_data = builder.delete_islocated_nodes_by_label(WikiDataConstance.LABEL_WIKIDATA)

        v2_1_graph_data.save(output_graph_data_path)

    def delete_relations_with_operation(self, graph_data):
        class_node_ids = graph_data.get_node_ids_by_label("class")
        for class_node_id in class_node_ids:
            class_out_relation = graph_data.get_all_out_relations(class_node_id)
            for s, r, e in class_out_relation:
                end_node = graph_data.get_node_info_dict(e)
                if r == "has operation" and "operation" in end_node["labels"]:
                    # print("remove class-operation startid=%d, relation=%s, end_id=%s" % (s, r, e))
                    graph_data.remove_relation(s, r, e)

        domain_node_ids = graph_data.get_node_ids_by_label("domain term")
        for domain_node_id in domain_node_ids:
            domain_out_relation = graph_data.get_all_out_relations(domain_node_id)
            for s, r, e in domain_out_relation:
                end_node = graph_data.get_node_info_dict(e)
                if r == "can be operated" and "operation" in end_node["labels"]:
                    # print("remove domain-operation startid=%d, relation=%s, end_id=%s" % (s, r, e))
                    graph_data.remove_relation(s, r, e)
        print("add reverse edges finished!!")
        graph_data.refresh_indexer()

        return graph_data

    def add_reverse_edge(self, graph_data):
        reverse_relation_map = {
            "belong to": "has",
            "extends": "is extended by",
            "implements": "is implemented by",
            "see also": "see also",
            "thrown exception type": "exception type thrown by",
            "return value type": "type returned by",
            "has parameter": "is parameter of",
            "has return value": "is return value of",
            "has exception condition": "exception condition thrown by",
            "has field": "is field of",
            "type of": "has type instance",
            "call method": "method be called",
            "use class": "class be used by",
            "call field": "field be called",
            "overriding": "overriding by",
            "overloading": "overloading by",
            "subclass of": "superclass of",
            "use local variable": "local variable be used by",
            "array of": "has array",
            RelationType.IS_A: "superclass of",
            RelationType.DERIVED_FROM: "has part",
            RelationType.MENTION_IN_COMENT: "mentioned in comment",
            RelationType.MENTION_IN_INSIDE_COMENT: "mentioned in inside comment",
            RelationType.MENTION_IN_STRING_LITERAL: "mentioned in string literal",
            RelationType.MENTION_IN_SHORT_DESCRIPTION: "mentioned in short description",

            RelationType.REPRESENT: "represented by",
            RelationType.NAME_MENTION: "mentioned in name",

        }
        wiki_reverse_relation_map = {
            "subclass of": "superclass of",
            "instance of": "superclass of",
            "part of": "has part"
        }

        all_relations = graph_data.get_relation_pairs_with_type()
        for start_id, relation, end_id in all_relations:
            current_start_node = graph_data.get_node_info_dict(start_id)
            current_end_node = graph_data.get_node_info_dict(end_id)
            if "wikidata" in current_start_node["labels"] and "wikidata" in current_end_node["labels"]:
                if relation in wiki_reverse_relation_map:
                    graph_data.add_relation(end_id, wiki_reverse_relation_map[relation], start_id)
                    print("add new wiki relation: startid=%d, relation=%s, end_id=%s" % (
                        end_id, wiki_reverse_relation_map[relation], start_id))
            else:
                if relation in reverse_relation_map:
                    graph_data.add_relation(end_id, reverse_relation_map[relation], start_id)
                    print("add new wiki relation: startid=%d, relation=%s, end_id=%s" % (
                        end_id, reverse_relation_map[relation], start_id))

                if relation.startswith("operation_"):
                    graph_data.add_relation(end_id, relation.replace("operation_", "operated_"), start_id)
                    print("add new wiki relation: startid=%d, relation=%s, end_id=%s" % (
                        end_id, relation.replace("operation_", "operated_"), start_id))

        return graph_data
