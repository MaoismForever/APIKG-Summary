from script.summary.generate_summary import Summary
from util.path_util import PathUtil

if __name__ == '__main__':
    pro_name = "jdk8"
    version = "v3_1"
    compound_model_name = "compound_{base_model}+{extra_model}".format(base_model="avg_w2v", extra_model="svm")
    model_dir = PathUtil.sim_model(pro_name=pro_name, version=version, model_type=compound_model_name)
    summary = Summary(pro_name, version, model_dir)
    while True:
        query = input("please input query:")
        all_class_2_summary = summary.get_summary_only_query_by_method(query, 66)
        for index, item in all_class_2_summary.items():
            print(index, item)
