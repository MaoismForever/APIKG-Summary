import json

from sekg.graph.accessor import GraphAccessor
from sekg.graph.exporter.graph_data import Neo4jImporter, GraphData
from sekg.term.fusion import Fusion
from sekg.text.extractor.domain_entity.entity_extractor import EntityExtractor

from definitions import GRAPH_FACTORY
from util.graph_load_util import GraphLoadUtil
from util.import_extract_result_2_graph_data import ExtractResultImport
from util.path_util import PathUtil

test = GraphLoadUtil();
collection = GraphLoadUtil.load_doc("android27", "v1")


docs = collection.get_document_list()
graph_data_path = PathUtil.graph_data(pro_name="android27", version="v1")
graph_data: GraphData = GraphData.load(graph_data_path)
new_graph_data_path = PathUtil.graph_data(pro_name="android27", version="v3")
res = ExtractResultImport(graph_data, new_graph_data_path, 3)
sentences_entity = EntityExtractor()
num = 1
fused_domain = {}
not_fused_domain = []
domain_judge_fused = Fusion()


def text_save(filename, data):
    # file = open(filename, 'a')
    # for i in range(len(data)):
    #     s = str(data[i]).replace('[', '').replace(']', '')
    #     s = s.replace("'", '').replace(',', '') + '\n'
    #     file.write(s)
    # file.close()
    jsObj = json.dumps(data)
    fileObject = open(filename, 'w')
    fileObject.write(jsObj)
    print("保存文件成功")

def judge_domain(domain_term):
    # global fused_domain, domain_judge_fused
    if domain_term in fused_domain.keys():
        return domain_term
    for term_key, term_value in fused_domain.items():
        if domain_term in term_value:
            return term_key
        else:
            pass
    return domain_term

def get_fused_domain():
    # global fused_domain
    i = 0
    num_length = len(docs)
    for doc in docs:
        i = i + 1
        print('第%d次文本概念抽取,总共%d次' % (i,num_length))
        # if i > 10:
        #     break
        # else:
        #     i = i+1
        short_descs = doc.get_doc_text_by_field('short_description_sentences')
        for short_desc in short_descs:
            domain_terms, code_elements = sentences_entity.extract_from_sentence(short_desc)
            for domain_term in domain_terms:
                not_fused_domain.append(domain_term)
    print('开始别名识别中……')
    # print(not_fused_domain)
    synsets = domain_judge_fused.fuse_by_synonym(not_fused_domain)
    for synset in synsets:
        fused_domain[synset.key] = list(synset.terms)
    print(fused_domain.keys())
    print('别名识别完成')
    try:
        text_save('fused_domain_v1.json', fused_domain)
    except:
        print('fused_domain文件写入失败')

def build_graph_from_v1_2_v3():
    i = 0
    num_length = len(docs)
    for doc in docs:
        i = i + 1
        print('第%d次文本概念抽取,并插入节点,总共%d次' % (i, num_length))
        # if i > 5:
        #     break
        # else:
        #     i = i + 1
        id = doc.get_document_id()
        short_descs = doc.get_doc_text_by_field('short_description_sentences')
        for short_desc in short_descs:
            sentence_id = res.add_sentence_relation(short_desc, id)
            domain_terms, code_elements = sentences_entity.extract_from_sentence(short_desc)
            for domain_term in domain_terms:
                domain_term = judge_domain(domain_term)
                res.add_concept_relation(domain_term, sentence_id, 'concept')
    res.save_new_graph_data()


# get_fused_domain()
build_graph_from_v1_2_v3()
print('运行结束')
# print(domain_judge_fused.check_synonym('file', 'files'))



