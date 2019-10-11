from db.wiki_model import WikidataAnnotation, WikidataAnnotation1, WikidataAnnotation2, ClassifiedWikipediaDocumentLR, \
    WikidataAndWikipediaData
from definitions import MYSQL_FACTORY, WIKI_DIR
import pickle
from pathlib import Path


class exportWikidata:
    """
    for export wiki releated data from mysql
    """

    def __init__(self):
        self.session = MYSQL_FACTORY.create_mysql_session_by_server_name(server_name="73CodeHub",
                                                                         database="codehub",
                                                                         echo=True)

    def exportAnnotation(self, AnnotationClass, path):
        result = self.session.query(AnnotationClass).distinct().all()
        result_data = []
        for item in result:
            item_dic = {"id": item.id, "wd_item_id": item.wd_item_id, "type": item.type, "url": item.url,
                        "name": item.name, "description": item.description}
            result_data.append(item_dic)
        self.save(result_data, path)

    def exportClassification(self, path):
        result = self.session.query(ClassifiedWikipediaDocumentLR).filter(ClassifiedWikipediaDocumentLR.type == 1).all()
        save_data = []
        for item in result:
            url = item.url
            wiki = self.session.query(WikidataAndWikipediaData).filter(
                WikidataAndWikipediaData.wikipedia_url == url).first()
            if wiki:
                save_dic = {"url": url, "score": item.score,
                            "wekipedia_title": item.title,
                            "wd_item_name": wiki.wd_item_name,
                            "wd_item_id": wiki.wd_item_id}
                print(save_dic)
                save_data.append(save_dic)
        self.save(save_data, path)

    def save(self, data, path):
        with open(path, "wb") as fw:
            pickle.dump(data, fw)
        print("save {} data into {} done!".format(len(data), path))


if __name__ == '__main__':
    wiki_exporter = exportWikidata()
    wiki_dir = Path(WIKI_DIR)
    wiki_dir.mkdir(exist_ok=True, parents=True)
    path = str(wiki_dir / "WikidataAnnotation.pc")
    wiki_exporter.exportAnnotation(WikidataAnnotation, path)
    path_1 = str(wiki_dir / "WikidataAnnotation1.pc")
    wiki_exporter.exportAnnotation(WikidataAnnotation1, path_1)
    path_2 = str(wiki_dir / "WikidataAnnotation2.pc")
    wiki_exporter.exportAnnotation(WikidataAnnotation2, path_2)
    path_classification = str(wiki_dir / "WikidataClassification.pc")
    wiki_exporter.exportClassification(path_classification)
