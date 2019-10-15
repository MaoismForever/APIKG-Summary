from script.generate_summary import Summary

if __name__ == '__main__':
    summary = Summary()
    input_query = "How can I read input from the console using the Scanner class in Java?"
    summary.get_summary_only_query(input_query, 66)
    # summary.get_summary_only_query_by_method(input_query, 66)
    # summary.get_summary_only_query_by_sentence(input_query, 66)
