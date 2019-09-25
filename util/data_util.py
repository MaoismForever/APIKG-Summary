import json
from pathlib import Path


class EntityReader:
    @staticmethod
    def write_line_data(file_path,data):
        if file_path is not None:
            with Path(file_path).open("w") as f:
                f.write("\n".join(sorted(data, key=lambda x: x)))
    @staticmethod
    def read_line_data(file_path):
        if file_path is not None:
            with Path(file_path).open("r") as f:
                return [line.strip() for line in f]
        return []

    @staticmethod
    def read_json_data(file_path):
        if file_path is not None:
            with Path(file_path).open("r") as f:
                return json.load(f)

        return None

    @staticmethod
    def write_json_data(file_path, data, indent=4):
        if file_path is not None:
            with Path(file_path).open("w") as f:
                return json.dump(data, f, indent=4)

        return None
