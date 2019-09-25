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

# the output dir
BENCHMARK_DIR = os.path.join(ROOT_DIR, "benchmark")

# extracte_data dir
EXTRACTE_DATA_DIR = os.path.join(ROOT_DIR, "extracte_result")

## support all project
SUPPORT_PROJECT_LIST = [
    # "JabRef-2.6",
    # "jedite-4.3",
    # "ArgoUML-0.22",
    # "mucommander-0.8.5",
    # "Eclipse-3.0",

    # "ArgoUML-0.24",
    # "ArgoUML-0.26.2",
    # "derby-10.9.1.0",
    # "mahout-distribution-0.8",
    # "jedite-4.2",
    "jdk8"
    # "android27"

]

TEST_PROJECT_LIST = [
    "jedite-4.3",
    "JabRef-2.6",
]
