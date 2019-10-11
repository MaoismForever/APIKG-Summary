import os

from sekg.graph.factory import GraphInstanceFactory
from sekg.mysql.factory import MysqlSessionFactory

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  # This is your Project Root
NEO4J_CONFIG_PATH = os.path.join(ROOT_DIR, 'neo4j_config.json')
GRAPH_FACTORY = GraphInstanceFactory(NEO4J_CONFIG_PATH)
MYSQL_CONFIG_PATH = os.path.join(ROOT_DIR, 'mysql_config.json')
MYSQL_FACTORY = MysqlSessionFactory(MYSQL_CONFIG_PATH)
DEFAULT_MYSQL_SERVER = "87RootServer"

# project data
DATA_DIR = os.path.join(ROOT_DIR, 'data')

# the output dir
OUTPUT_DIR = os.path.join(ROOT_DIR, 'output')
WIKI_DIR = os.path.join(OUTPUT_DIR, 'wiki')

# the benchmark dir
BENCHMARK_DIR = os.path.join(ROOT_DIR, "benchmark")

# extracte_data dir
EXTRACTE_DATA_DIR = os.path.join(ROOT_DIR, "extracte_result")

## support all project
SUPPORT_PROJECT_LIST = [
    "jdk8"
]
