import spacy
import neuralcoref
import operator
import re

from sekg.util.code import CodeElementNameUtil


class ReferenceResolution:
    def __init__(self, nlp=None):
        if nlp is None:
            self.nlp = spacy.load('en', disable=["ner"])
        else:
            self.nlp = nlp
        neuralcoref.add_to_pipe(self.nlp, greedyness=0.5)
        self.code_element_name_util = CodeElementNameUtil()

    @staticmethod
    def replace_with_start_end(start, end, word, text):
        """
        根据起点和终点替换字符串
        :param start:
        :param end:
        :param word:
        :param text:
        :return:
        """
        result = text[:start] + word + text[end:]
        return result

    @staticmethod
    def replace_word_in_string(name_replace_list, text):
        """
        根据起始位置、终止位置、替换单词
        :param name_replace_list:
        :param text:
        :return:
        """
        result = text
        name_replace_list.sort(key=operator.itemgetter(0), reverse=True)
        for name_replace in name_replace_list:
            start_pos, end_pos, old_word, new_word = name_replace
            result = ReferenceResolution.replace_with_start_end(start_pos, end_pos, new_word, result)
        return result

    @staticmethod
    def word_num(text):
        """
        有多少个词
        :param text:
        :return: num int
        """
        return len(str(text).split(" "))

    def lemma_word(self, word):
        """
        词性还原
        :param word:
        :return:
        """
        doc = self.nlp(word)
        result = []
        for token in doc:
            if token.lemma_ == "-PRON-":
                result.append(token.norm_)
            else:
                result.append(token.lemma_)
        return " ".join(result)

    def maybe_contain_api(self, name):
        """
        判断name里面是否可能包含API
        :param name:
        :return: True or False
        """
        if name is None or str(name) == "":
            return False

        uncamelize = self.code_element_name_util.uncamelize(name.strip()).replace("( ", "(")
        if len(name.strip().split(" ")) < len(uncamelize.strip().split(" ")) or self.check_upper_case(name):
            return True
        return False

    def check_pronoun(self, word):
        doc = self.nlp(word)
        for token in doc:
            if token.lemma_ == '-PRON-':
                return True
        # pronoun_set = {
        #     "it", "that", "this", "these", "those",
        #     "which", "one", "ones", "they", "other", "another"
        # }
        # for n in str(word).split(" "):
        #     if n in pronoun_set:
        #         return True
        return False

    @staticmethod
    def replace_ignore_case(text, old, new, ):
        reg = re.compile(re.escape(old), re.IGNORECASE)
        return str(reg.sub(new, text))

    def remove_reference_with_context(self, context, text, input_doc=None):
        """

        :param input_doc:
        :param context: 一个字典，可以传入方法需要的上下文信息，
        package 信息，class信息，method信息，文档归属对象类型
        :param text: 文本
        :return: text，每句话的改动
        """
        # 按照词数目进行过滤
        skip_size = 4
        may_be_class_set = {"this class", "the class", "this interface", "the interface"}
        if input_doc is None:
            doc = self.nlp(text)
        else:
            doc = input_doc
        row = doc.text
        result = []
        if doc._.coref_clusters is None:
            return row
        for cluster in doc._.coref_clusters:
            try:
                new_word = cluster.main.text
                if ReferenceResolution.word_num(new_word) >= skip_size:
                    continue
                for men in cluster.mentions:
                    if cluster.main.text == men.text:
                        continue
                    old_word = men.text
                    start_pos = men.start_char
                    end_pos = men.end_char
                    for may_class in may_be_class_set:
                        if self.lemma_word(new_word).find(may_class) >= 0:
                            new_word = context["qn"]
                    if new_word == "":
                        continue
                    # 判断old_word是否已经是API了,已经是了就不替换
                    if self.maybe_contain_api(old_word) or self.lemma_word(old_word) == self.lemma_word(
                            new_word):
                        continue
                    # 判断old_word是否是代词，不是就continue
                    if not self.check_pronoun(old_word):
                        continue
                    # 判断new_word是否是API
                    if not self.maybe_contain_api(new_word):
                        continue
                    result.append((start_pos, end_pos, old_word, new_word))
            except Exception as e:
                print(e)
        after_text = ReferenceResolution.replace_word_in_string(result, row)
        after_text = ReferenceResolution.replace_ignore_case(after_text, "this one", context["qn"])
        after_text = ReferenceResolution.replace_ignore_case(after_text, "this class", context["qn"])
        return after_text, result

    @staticmethod
    def check_upper_case(text):
        """
        判断文本里面是否包含了驼峰式的class
        :param text:
        :return:
        """
        splited = str(text).split(" ")
        for i, s in enumerate(splited):
            if i > 0 and s[0].isupper():
                return True
        return False


if __name__ == '__main__':
    r = ReferenceResolution()
    # print(r.maybe_contain_api("The class is a"))
    s = """A mutable sequence of characters. This class provides an API compatible with StringBuffer, but with no guarantee of synchronization. This class is designed for use as a drop-in replacement for StringBuffer in places where the string buffer was being used by a single thread (as is generally the case). Where possible, it is recommended that this class be used in preference to StringBuffer as it will be faster under most implementations.
The principal operations on a StringBuilder are the append and insert methods, which are overloaded so as to accept data of any type. Each effectively converts a given datum to a string and then appends or inserts the characters of that string to the string builder. The append method always adds these characters at the end of the builder; the insert method adds the characters at a specified point.

For example, if z refers to a string builder object whose current contents are "start", then the method call z.append("le") would cause the string builder to contain "startle", whereas z.insert(4, "le") would alter the string builder to contain "starlet".

In general, if sb refers to an instance of a StringBuilder, then sb.append(x) has the same effect as sb.insert(sb.length(), x).

Every string builder has a capacity. As long as the length of the character sequence contained in the string builder does not exceed the capacity, it is not necessary to allocate a new internal buffer. If the internal buffer overflows, it is automatically made larger.

Instances of StringBuilder are not safe for use by multiple threads. If such synchronization is required then it is recommended that StringBuffer be used."""
    context = {"qn": "java.lang.StringBuilder"}
    tmp = "it"
    r.lemma_word(tmp)
    remove_result_text, change_list = r.remove_reference_with_context(context, s)
    # r.remove_reference(s)
    print(remove_result_text)
