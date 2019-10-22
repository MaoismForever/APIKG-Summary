# encoding=utf-8
import os
from pyfasttext import FastText
from definitions import DATA_DIR, OUTPUT_DIR
from pathlib import Path

from script.fast_text.preprocess_data import PreprocessData

data_dir = Path(DATA_DIR) / 'dataset for fast_text'
data_dir.mkdir(parents=True, exist_ok=True)
train_data_path = str(data_dir / 'fast_text_train_data.txt')
test_data_path = str(data_dir / 'fast_text_test_data.txt')
ori_json_path = str(data_dir / 'annotation_sentence_vote_valid.json')
model_dir = Path(OUTPUT_DIR) / 'fast_text model'
model_dir.mkdir(parents=True, exist_ok=True)


class FastTextClassifier:
    def __init__(self):
        self.classifier = None
        self.model_path = str(model_dir / 'classifier.model')
        self.preprocessor = PreprocessData()
        self.load_model()

    def load_model(self, ):
        if os.path.exists(self.model_path):
            self.classifier = FastText(self.model_path)
        else:
            self.train_model()
            print("no such model, model now")

    def set_model_path(self, new_path):
        self.model_path = new_path

    def train_model(self):
        classifier = FastText.supervised(input=train_data_path, output=model_dir, lr=0.25, ws=4)
        classifier.save_model(self.model_path)
        self.classifier = classifier
        print("test result in training data:")
        result = classifier.test(train_data_path)
        print(result)
        print("test result in testing data:")
        result = classifier.test(test_data_path)
        print(result)

    def predict(self, text):
        """
        :param text: a str query
        :return: predicted label of the input sentence
        """
        rmsign_text = self.preprocessor.remove_sign(text)
        pre_data = self.preprocessor.remove_stop_words(rmsign_text)
        if len(text.split()) <= 2:
            b = ('0',)
            return b
        label = self.classifier.predict_single(pre_data)

        try:
            return label[0]
        except:
            b = ('0',)
            return b


if __name__ == "__main__":
    classifier = FastTextClassifier()
    classifier.predict("()")
    classifier.predict("Returns the authorization")
