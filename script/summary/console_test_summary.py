from script.summary.generate_summary import Summary

if __name__ == '__main__':
    summary = Summary()
    while True:
        query = input("please input query:")
        all_class_2_summary = summary.get_summary_only_query(query, 66)
        for index, item in all_class_2_summary.items():
            print(index, item)
    # input_query = "How can I read input from the console using the Scanner class in Java?"
    # summary.get_summary_only_query_by_method(input_query, 66)
    # summary.get_summary_only_query_by_sentence(input_query, 66)
