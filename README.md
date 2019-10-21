## APISummary
1. This is an official implementation of ["Generating Query-Specific Class API Summaries"](http://delivery.acm.org/10.1145/3340000/3338971/fse19main-id291-p.pdf?ip=202.120.235.96&id=3338971&acc=ACTIVE%20SERVICE&key=BF85BBA5741FDC6E%2E88014DC677A1F2C3%2E4D4702B0C3E38B35%2E4D4702B0C3E38B35&__acm__=1571655121_84ed7bca1423a0de5476d7125a940c42).  
2. APISummary is a project of creating API summary when given specific query and class. We construct an API Knowledge Graph with api documentation and wikidata knowledge to minish the gap between different types of knowledge.
3. The available experiment data is [here](https://fudanselab.github.io/Research-ESEC-FSE2019-APIKGSummary/), other data for model is [here]()

## Requiment
1. sekg  (an integrated python package of our research)
2. pyfasttext  
3. gensim
4. py2neo
5. nltk

## Project module description
- db:   
data table in database
- doc:   
some classes for building documents for training model  
- graph:   
graph builder for generating graph
- script:  
scripts for building documents, building graph, training model, generating summary and importing graph data into neo4j. You can easily find by their name.  
- util:   
some general tool classes

## Quickstart
Our project consists of three main parts: build api graph, train search model and generate apisummary.  

1、build graph and document     
   ``` 
   pyhon -m script.build_all_graph_and_doc  
   ``` 
   
    
2、train model  
   ``` 
   python -m script.n2v.train   
   python -m script.model.compound.train
   ```
3、summary 
   ``` 
   python -m script.summary.console_test_summary_with_class
   ```
  

## Citation
When citing ["Generating Query-Specific Class API Summaries"](http://delivery.acm.org/10.1145/3340000/3338971/fse19main-id291-p.pdf?ip=202.120.235.96&id=3338971&acc=ACTIVE%20SERVICE&key=BF85BBA5741FDC6E%2E88014DC677A1F2C3%2E4D4702B0C3E38B35%2E4D4702B0C3E38B35&__acm__=1571655121_84ed7bca1423a0de5476d7125a940c42) in academic papers and theses, please use this BibTeX entry:
```
@inproceedings{DBLP:conf/sigsoft/Liu0MXXXL19,
  author    = {Mingwei Liu and
               Xin Peng and
               Andrian Marcus and
               Zhenchang Xing and
               Wenkai Xie and
               Shuangshuang Xing and
               Yang Liu},
  title     = {Generating query-specific class {API} summaries},
  booktitle = {Proceedings of the {ACM} Joint Meeting on European Software Engineering
               Conference and Symposium on the Foundations of Software Engineering,
               {ESEC/SIGSOFT} {FSE} 2019, Tallinn, Estonia, August 26-30, 2019.},
  pages     = {120--130},
  year      = {2019},
  crossref  = {DBLP:conf/sigsoft/2019},
  url       = {https://doi.org/10.1145/3338906.3338971},
  doi       = {10.1145/3338906.3338971},
  timestamp = {Fri, 09 Aug 2019 14:13:18 +0200},
  biburl    = {https://dblp.org/rec/bib/conf/sigsoft/Liu0MXXXL19},
  bibsource = {dblp computer science bibliography, https://dblp.org}
}
```