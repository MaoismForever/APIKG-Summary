import spacy
import neuralcoref

clean_nlp = spacy.load('en_core_web_sm', disable=["ner", "textcat"])
neuralcoref.add_to_pipe(clean_nlp, greedyness=0.5)


def get_sentence_list(text):
    l = []
    test_doc = clean_nlp(text)
    for sent in test_doc.sents:
        l.append(sent.text)
    return l


def clean_pure_code_sentence(text: str):
    text = text.strip()
    after_split = str(text).split("/")
    if len(after_split) <= 1:
        return text
    if text.find(" ") < 0:
        return ""
    if text.find(".java") > (len(text) / 2):
        return ""
    return text


def get_sentence_list_with_doc(doc):
    l = []
    for sent in doc.sents:
        clean = clean_pure_code_sentence(sent.text)
        if clean == "":
            continue
        l.append(clean)
    return l


if __name__ == '__main__':
    description = """The StringBuilder class should generally be used in preference to this one, as it supports all of the same operations but it is faster, as it performs no synchronization."""
    short_description_doc = clean_nlp(description)
    get_sentence_list_with_doc(short_description_doc)
