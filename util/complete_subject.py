import spacy
from sekg.text.extractor.domain_entity.word_util import WordUtil


class CompleteSubject:
    def __init__(self, nlp=None):
        if nlp is None:
            self.nlp = spacy.load('en', disable=["ner"])
        else:
            self.nlp = nlp

    def complete_subject_by_name_for_doc(self, full_doc, sentence_belong_name, doc=None):
        if doc is not None:
            test_doc = doc
        else:
            test_doc = self.nlp(full_doc)
        result = []
        for sent in test_doc.sents:
            result.append(self.complete_subject_by_name_for_sentence(sent.text, sentence_belong_name, sent))
        return " ".join(result), test_doc

    def how_many_upper(self, input_text):
        """
        有多少个大写字符
        :param input_text:
        :return:
        """
        n = 0
        for l, r in zip(input_text.lower(), input_text):
            if l != r:
                n += 1
        return n

    def complete_subject_by_name_for_sentence(self, text, sentence_belong_name, sent):
        """
        根据文档所属的全限定名，补全
        先分析
        :param sent:
        :param text:
        :param sentence_belong_name:
        :return:补全后的句子
        """
        lower_text = str(text).lower()
        if self.check_has_main_subject(sent) or lower_text.lower().find(" this ") >= 0:
            return text
        else:
            for i, doc in enumerate(sent):
                if i == 0:
                    if WordUtil.couldBeVerb(doc.text):
                        f = str(text[0]).lower()
                        sentence = sentence_belong_name + " " +  f + text[1:]
                        return sentence
                    else:
                        if self.how_many_upper(doc.text) > 1:
                            sentence = sentence_belong_name + " is " + text
                            return sentence
                        else:
                            f = str(text[0]).lower()
                            sentence = sentence_belong_name + " is " + f + text[1:]
                            return sentence

    def check_has_main_subject(self, sent):
        # doc = self.nlp(text)
        for i, d in enumerate(sent):
            if i == 0 and d.dep_ == 'auxpass':
                return False
            if "nsubj" == d.dep_ and d.text != "that":
                return True
        return False


if __name__ == '__main__':
    cs = CompleteSubject()
    s = """A mutable sequence of characters. This class provides an API compatible with StringBuffer, but with no guarantee of synchronization. This class is designed for use as a drop-in replacement for StringBuffer in places where the string buffer was being used by a single thread (as is generally the case). Where possible, it is recommended that this class be used in preference to StringBuffer as it will be faster under most implementations.
The principal operations on a StringBuilder are the append and insert methods, which are overloaded so as to accept data of any type. Each effectively converts a given datum to a string and then appends or inserts the characters of that string to the string builder. The append method always adds these characters at the end of the builder; the insert method adds the characters at a specified point.

For example, if z refers to a string builder object whose current contents are "start", then the method call z.append("le") would cause the string builder to contain "startle", whereas z.insert(4, "le") would alter the string builder to contain "starlet".

In general, if sb refers to an instance of a StringBuilder, then sb.append(x) has the same effect as sb.insert(sb.length(), x).

Every string builder has a capacity. As long as the length of the character sequence contained in the string builder does not exceed the capacity, it is not necessary to allocate a new internal buffer. If the internal buffer overflows, it is automatically made larger.

Instances of StringBuilder are not safe for use by multiple threads. If such synchronization is required then it is recommended that StringBuffer be used."""
    s = 'obtain a reference to a bootstrap remote object registry on a particular host (including the local host), or to create a remote object registry that accepts calls on a specific port.'
    # java.lang.StringBuffer is A thread-safe, mutable sequence of characters.
    s = "A thread-safe, mutable sequence of characters. "
    after = cs.complete_subject_by_name_for_doc(s, "java.lang.StringBuilder")
    # after = cs.complete_subject_by_name_for_doc(s, "java.lang.StringBuffer")
    print(after)
