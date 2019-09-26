import json
from pathlib import Path

from flask import Flask, request, jsonify
from sekg.graph.exporter.graph_data import GraphData
import sys
sys.path.append('/home/fdse/lvgang/APIKGSummaryV1')

from definitions import OUTPUT_DIR
from script.generate_summary import Summary
from util.path_util import PathUtil
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
# graph_data_path = PathUtil.graph_data(pro_name="jdk8", version="v3")
# graph_data: GraphData = GraphData.load(graph_data_path)
# model_dir = Path(OUTPUT_DIR) / "search_model" / "compound_newest"
# model = create_search_model(model_dir)
summary = Summary()


@app.route('/')
def hello_world():
    return 'Hello World!!!'


@app.route('/createAPISummary/', methods=['POST'])
def create_api_summary():
    request_body = request.json
    query = request_body['query'].strip()
    class_name_or_number = request_body['class_name_or_number'].strip()
    if query != '' and query is not None and class_name_or_number != '' and class_name_or_number is not None:
        class_or_method_2_sentence = {}
        if class_name_or_number.isdigit():
            class_number = int(class_name_or_number)
            # class_or_method_2_sentence = jsonify(get_summary_only_query(graph_data, query, model, class_number))
            class_or_method_2_sentence = jsonify(summary.get_summary_only_query(query, 66))
        else:
            a = {0: summary.get_summary(query, class_name_or_number)}
            class_or_method_2_sentence = jsonify(a)
        return class_or_method_2_sentence


if __name__ == '__main__':
    app.run()
