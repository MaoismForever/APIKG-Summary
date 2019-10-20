import json
import random
import sys
from pathlib import Path
from definitions import DATA_DIR
from nltk import WordPunctTokenizer
from nltk.corpus import stopwords

data_dir = Path(DATA_DIR) / 'dataset for fast_text'
data_dir.mkdir(parents=True, exist_ok=True)
train_data_path = str(data_dir / 'fast_text_train_data.txt')
test_data_path = str(data_dir / 'fast_text_test_data.txt')
predict_data_path = str(data_dir / 'fast_text_predict_data.txt')


class PreprocessData:
    def __init__(self, data_path=None):
        self.data_path = data_path

    def get_data_from_json(self, ):
        """
        :param path: path of a json file
        :return: json_list data
        """
        try:
            with open(self.data_path, 'r', encoding="utf-8") as json_file:
                load_dict = json.load(json_file)
                json_file.close()
            return load_dict
        except Exception as e:
            print("exception:" + str(e))

    def remove_sign(self, str):
        """
        remove sign code of sentence
        input;str
        :return: str
        """
        remove_list = ["\n", "\t", "\r", "/", "*", ".", ";", "@", "{", "}", "<p>", "(", ")", "#", "=", ":", "+", "-",
                       "!", "[", "]", ",", ":", "<", ">", "|", "\\", "&", "'", "?", "\""]
        new_str = str
        for item in remove_list:
            new_str = new_str.replace(item, " ")
        return new_str

    def remove_stop_words(self, sentence):
        """
        remove stop_words of sentence
        :param sentence:
        :return:
        """
        words = WordPunctTokenizer().tokenize(sentence)
        st = stopwords.words('english')
        str_list = []
        for token in words:
            if token not in st:
                str_list.append(token)
        return " ".join(str_list)

    def clean_data(self, sentence):
        text = sentence.lower()
        str_rm_sign = self.remove_sign(text)
        str_rm_stop = self.remove_stop_words(str_rm_sign)
        return str_rm_stop

    def fast_text_data(self, sentence_list):
        """
        change sentence_list into fast_text format
        :param sentence_list: the origin sentence from the json dataset
        :return: Preprocessed data
        """
        data_list = []
        for item in sentence_list:
            clean_text = self.clean_data(item["text"])
            data_list.append("__label__" + str(item["vote_type"]) + " , " + clean_text)
        random.shuffle(data_list)
        return data_list

    def write_data(self, sentences, fileName):
        print("writing data to fasttext format")
        try:
            out = open(fileName, 'w', encoding="utf-8")
            for sentence in sentences:
                out.write(sentence + "\n")
            print("done!")
        except Exception as e:
            print("exception:" + str(e))

    def save_train_and_test_data(self, fast_text_data_list):
        seg_num = int(len(fast_text_data_list) * 0.8)
        self.write_data(fast_text_data_list[:seg_num], train_data_path)
        self.write_data(fast_text_data_list[seg_num + 1:], test_data_path)

    def preprocess(self, ):
        sentence_data = preprocessor.get_data_from_json()
        fast_text_data = self.fast_text_data(sentence_data)
        self.save_train_and_test_data(fast_text_data)


if __name__ == "__main__":
    ori_json_path = str(data_dir / 'annotation_sentence_vote_valid.json')
    preprocessor = PreprocessData(ori_json_path)
    preprocessor.preprocess()
