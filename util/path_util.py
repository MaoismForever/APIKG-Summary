from pathlib import Path

from definitions import OUTPUT_DIR, BENCHMARK_DIR, DATA_DIR


class PathUtil:
    """
    provide a way to get a path to specific model
    """

    @staticmethod
    def name_searcher(pro_name, version):
        graph_data_output_dir = Path(OUTPUT_DIR) / "graph" / pro_name
        graph_data_output_dir.mkdir(exist_ok=True, parents=True)
        name_searcher_output_dir = graph_data_output_dir / "NameSearcher"
        name_searcher_output_dir.mkdir(exist_ok=True, parents=True)
        name_searcher_path = str(
            name_searcher_output_dir / "{pro}.{version}.namesearcher".format(pro=pro_name, version=version))

        return name_searcher_path

    @staticmethod
    def graph_data(pro_name, version):
        graph_data_output_dir = Path(OUTPUT_DIR) / "graph" / pro_name
        graph_data_output_dir.mkdir(exist_ok=True, parents=True)

        graph_data_path = str(graph_data_output_dir / "{pro}.{version}.graph".format(pro=pro_name, version=version))
        return graph_data_path

    @staticmethod
    def graph_edge_weight(pro_name, version):
        graph_data_output_dir = Path(OUTPUT_DIR) / "graph" / pro_name / "GraphEmbedding"
        graph_data_output_dir.mkdir(exist_ok=True, parents=True)

        graph_data_path = str(graph_data_output_dir / "{pro}.{version}.edge.list".format(pro=pro_name, version=version))
        return graph_data_path

    @staticmethod
    def jdk_graph_data():
        jdk_graph_data_dir = Path(OUTPUT_DIR) / "graph" / "jdk8"
        jdk_graph_data_dir.mkdir(exist_ok=True, parents=True)

        jdk_graph_data_path = str(jdk_graph_data_dir / ("jdk8" + ".v1.graph"))
        return jdk_graph_data_path


    @staticmethod
    def jdk_api_node_map():
        jdk_graph_data_dir = Path(OUTPUT_DIR) / "graph" / "jdk8"
        jdk_graph_data_dir.mkdir(exist_ok=True, parents=True)

        id_map_file_path = str(jdk_graph_data_dir / ("jdk8" + ".api2node.map"))

        return id_map_file_path

    @staticmethod
    def domain_jdk_graph_data():
        jdk_graph_data_dir = Path(OUTPUT_DIR) / "graph" / "jdk8"
        jdk_graph_data_dir.mkdir(exist_ok=True, parents=True)
        jdk_graph_data_path = str(jdk_graph_data_dir / ("jdk8" + ".v2.graph"))
        return jdk_graph_data_path

    @staticmethod
    def wikidata_jdk_graph_data():
        jdk_graph_data_dir = Path(OUTPUT_DIR) / "graph" / "jdk8"
        jdk_graph_data_dir.mkdir(exist_ok=True, parents=True)
        jdk_graph_data_path = str(jdk_graph_data_dir / ("jdk8" + ".v3.graph"))
        return jdk_graph_data_path

    @staticmethod
    def doc(pro_name, version):
        doc_output_dir = PathUtil.doc_dir(pro_name)
        doc_path = str(
            Path(doc_output_dir) / ("{pro}.{version}.dc".format(pro=pro_name, version=version)))
        return doc_path

    @staticmethod
    def doc_dir(pro_name):
        doc_output_dir = Path(OUTPUT_DIR) / "doc" / pro_name
        doc_output_dir.mkdir(exist_ok=True, parents=True)
        return str(doc_output_dir)

    @staticmethod
    def pre_doc(pro_name, version, pre_way="code-pre"):
        doc_output_dir = PathUtil.doc_dir(pro_name)

        pre_doc_collection_out_path = str(Path(doc_output_dir) / (
            "{pro}.{version}.{pre_way}.dc".format(pro=pro_name, version=version, pre_way=pre_way)))

        return pre_doc_collection_out_path

    @staticmethod
    def pre_doc_multi_field(pro_name, version, pre_way="code-pre"):
        doc_output_dir = PathUtil.doc_dir(pro_name)

        pre_doc_collection_out_path = str(Path(doc_output_dir) / (
            "{pro}.{version}.{pre_way}.dc".format(pro=pro_name, version=version, pre_way=pre_way)))

        return pre_doc_collection_out_path

    @staticmethod
    def node2vec(pro_name, version, weight="unweight"):
        graph_data_output_dir = Path(OUTPUT_DIR) / "graph" / pro_name
        graph_data_output_dir.mkdir(exist_ok=True, parents=True)

        node2vec_output_dir = graph_data_output_dir / "GraphEmbedding"
        node2vec_output_dir.mkdir(exist_ok=True, parents=True)

        node2vec_path = str(
            node2vec_output_dir / "{pro}.{version}.{weight}.node2vec".format(pro=pro_name,
                                                                             version=version, weight=weight))

        return node2vec_path

    @staticmethod
    def tridnr(pro_name, version, weight="unweight"):
        graph_data_output_dir = Path(OUTPUT_DIR) / "graph" / pro_name
        graph_data_output_dir.mkdir(exist_ok=True, parents=True)

        node2vec_output_dir = graph_data_output_dir / "GraphEmbedding"
        node2vec_output_dir.mkdir(exist_ok=True, parents=True)

        node2vec_path = str(
            node2vec_output_dir / "{pro}.{version}.{weight}.tridnr".format(pro=pro_name,
                                                                           version=version, weight=weight))

        return node2vec_path

    @staticmethod
    def word2vec(pro_name):
        graph_data_output_dir = Path(OUTPUT_DIR) / "graph" / pro_name
        graph_data_output_dir.mkdir(exist_ok=True, parents=True)

        node2vec_output_dir = graph_data_output_dir / "WordEmbedding"
        node2vec_output_dir.mkdir(exist_ok=True, parents=True)

        node2vec_path = str(
            node2vec_output_dir / "{pro}.wordemb".format(pro=pro_name))

        return node2vec_path

    @staticmethod
    def tuned_word2vec(pro_name, version):
        graph_data_output_dir = Path(OUTPUT_DIR) / "graph" / pro_name
        graph_data_output_dir.mkdir(exist_ok=True, parents=True)

        node2vec_output_dir = graph_data_output_dir / "WordEmbedding"
        node2vec_output_dir.mkdir(exist_ok=True, parents=True)

        node2vec_path = str(
            node2vec_output_dir / "{pro}.{version}.tunrd.wordemb".format(pro=pro_name, version=version))

        return node2vec_path

    @staticmethod
    def rwp(pro_name, version, weight="unweight"):
        graph_data_output_dir = Path(OUTPUT_DIR) / "graph" / pro_name
        graph_data_output_dir.mkdir(exist_ok=True, parents=True)

        node2vec_output_dir = graph_data_output_dir / "GraphEmbedding"
        node2vec_output_dir.mkdir(exist_ok=True, parents=True)

        return str(
            node2vec_output_dir / "{pro}.{version}.{weight}.rwp".format(pro=pro_name, version=version, weight=weight))

    @staticmethod
    def sim_model(pro_name, version, model_type):
        model_dir = Path(OUTPUT_DIR) / "sim_models" / pro_name / version / model_type
        model_dir.mkdir(exist_ok=True, parents=True)

        return str(model_dir)

    @staticmethod
    def domain_concept_dir(pro_name, version):
        graph_data_output_dir = Path(OUTPUT_DIR) / "graph" / pro_name
        graph_data_output_dir.mkdir(exist_ok=True, parents=True)

        domain_dir = graph_data_output_dir / "domain" / version
        domain_dir.mkdir(exist_ok=True, parents=True)
        return str(domain_dir)

    @staticmethod
    def wikidata_dir(pro_name):
        graph_data_output_dir = Path(OUTPUT_DIR) / "graph" / pro_name
        graph_data_output_dir.mkdir(exist_ok=True, parents=True)

        domain_dir = graph_data_output_dir / "wikidata"
        domain_dir.mkdir(exist_ok=True, parents=True)
        return str(domain_dir)


    @staticmethod
    def experiment_record(pro_name):
        experiment_store_dir = Path(OUTPUT_DIR) / "experiment"
        experiment_store_dir.mkdir(exist_ok=True, parents=True)
        experiment_recorder_path = experiment_store_dir / ("%s.record" % pro_name)
        return str(experiment_recorder_path)

    @staticmethod
    def path_based_experiment_record(pro_name):
        experiment_store_dir = Path(OUTPUT_DIR) / "experiment-path-based"
        experiment_store_dir.mkdir(exist_ok=True, parents=True)
        experiment_recorder_path = experiment_store_dir / ("%s.record" % pro_name)
        return str(experiment_recorder_path)

    @staticmethod
    def all_wikidata_dir():
        graph_data_output_dir = Path(OUTPUT_DIR) / "wikidata"
        graph_data_output_dir.mkdir(exist_ok=True, parents=True)

        return str(graph_data_output_dir)

    @staticmethod
    def pretrain():
        dir = Path(OUTPUT_DIR) / "pretrain"
        dir.mkdir(exist_ok=True, parents=True)

        return str(dir)

    @staticmethod
    def pretrain_wiki_w2v():
        dir = Path(OUTPUT_DIR) / "pretrain"
        dir.mkdir(exist_ok=True, parents=True)

        return str(dir / "pretrainwiki.100.w2v.bin")

    @staticmethod
    def corpus(pro_name, version):
        graph_data_output_dir = Path(OUTPUT_DIR) / "graph" / pro_name
        graph_data_output_dir.mkdir(exist_ok=True, parents=True)

        node2vec_output_dir = graph_data_output_dir / "Corpus"
        node2vec_output_dir.mkdir(exist_ok=True, parents=True)

        return str(
            node2vec_output_dir / "{pro}.{version}.corpus".format(pro=pro_name, version=version))

    @staticmethod
    def sim_model_multi_field(pro_name, version, model_type, field_name=None):
        if field_name:
            model_dir = Path(OUTPUT_DIR) / "sim_models" / pro_name / version / model_type / field_name
        else:
            model_dir = Path(OUTPUT_DIR) / "sim_models" / pro_name / version / model_type
        model_dir.mkdir(exist_ok=True, parents=True)
        return str(model_dir)

    @staticmethod
    def code_analysis_result_dir(pro_name):
        base_dir = Path(DATA_DIR) / "raw" / pro_name
        base_dir.mkdir(exist_ok=True, parents=True)
        return str(base_dir)

    @staticmethod
    def graph_data_output_dir(pro_name):
        d = Path(OUTPUT_DIR) / "graph" / pro_name
        d.mkdir(exist_ok=True, parents=True)
        return str(d)

    @staticmethod
    def wikipedia_context_cache():
        generic_cached_wikidata_dir = PathUtil.all_wikidata_dir()
        all_wikidata_dir = Path(generic_cached_wikidata_dir)
        generic_wikipedia_context_path = str(all_wikidata_dir / "wikipedia_context.bin")
        return generic_wikipedia_context_path

    @staticmethod
    def generic_wikidata_item_cache():
        generic_cached_wikidata_dir = PathUtil.all_wikidata_dir()
        all_wikidata_dir = Path(generic_cached_wikidata_dir)
        generic_wikidata_item_cache_path = str(all_wikidata_dir / "term_wikiitems.bin")
        return generic_wikidata_item_cache_path


    @staticmethod
    def project_wikidata_item_cache(pro_name):
        wikidata_dir = Path(PathUtil.wikidata_dir(pro_name))

        pro_wikidata_item_cache_path = str(wikidata_dir / "term_wikiitems.bin")

        return pro_wikidata_item_cache_path

    @staticmethod
    def wikidata_fusion_temp_result_dir(pro_name):

        return PathUtil.wikidata_dir(pro_name)

    @staticmethod
    def code_doc_collection(pro_name):
        doc_dir = PathUtil.doc_dir(pro_name)
        return str(Path(doc_dir) / "{pro}.v0.code.dc".format(pro=pro_name))


    @staticmethod
    def method_search_model(pro_name, model_type):
        model_dir = Path(OUTPUT_DIR) / "sim_models" / pro_name / "method_search" / model_type
        model_dir.mkdir(exist_ok=True, parents=True)
        return str(model_dir)
