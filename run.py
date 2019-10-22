from flask import Flask, request, jsonify
from script.summary.generate_summary import Summary
from flask_cors import CORS
from util.path_util import PathUtil

app = Flask(__name__)
CORS(app)
pro_name = "jdk8"
version = "v3_1"
compound_model_name = "compound_{base_model}+{extra_model}".format(base_model="avg_w2v", extra_model="svm")
model_dir = PathUtil.sim_model(pro_name=pro_name, version=version, model_type=compound_model_name)
summary = Summary(pro_name, version, model_dir)


@app.route('/createAPISummary/', methods=['POST'])
def create_api_summary():
    request_body = request.json
    query = request_body['query'].strip()
    class_name_or_number = request_body['class_name_or_number'].strip()
    if query != '' and query is not None and class_name_or_number != '' and class_name_or_number is not None:
        if class_name_or_number.isdigit():
            class_or_method_2_sentence = jsonify(summary.get_summary_only_query_by_method(query, 66))
        else:
            a = {0: summary.get_summary(query, class_name_or_number)}
            class_or_method_2_sentence = jsonify(a)
        return class_or_method_2_sentence


if __name__ == '__main__':
    app.run()
