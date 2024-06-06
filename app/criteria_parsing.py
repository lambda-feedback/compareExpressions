from .slr_parsing_utilities import SLR_Parser, catch_undefined, infix, create_node, operate, join, group, proceed, append_last

def generate_criteria_parser(reserved_expressions):
    start_symbol = "START"
    end_symbol = "END"
    null_symbol = "NULL"

    token_list = [
        (start_symbol,     start_symbol),
        (end_symbol,       end_symbol),
        (null_symbol,      null_symbol),
        (" *BOOL *",       "BOOL"),
        (" *EQUALITY *",   "EQUALITY"),
        (" *RESERVED *",   "RESERVED"),
        (" *= *",          "EQUAL"),
        (" *where *",      "WHERE"),
        (" *written as *", "WRITTEN_AS"),
        (" *; *", "SEPARATOR"),
        (" *OTHER *",      "OTHER", catch_undefined),
    ]

    for value in reserved_expressions.values():
        token_list += [(key, "RESERVED") for key in value.keys()]

    productions = [
        ("START",         "BOOL", create_node),
        ("BOOL",          "EQUALITY", proceed),
        ("BOOL",          "EQUALITY where EQUALITY", infix),
        ("BOOL",          "EQUALITY where EQUALITY_LIST", infix),
        ("EQUALITY",      "OTHER = OTHER", infix),
        ("EQUALITY",      "RESERVED = OTHER", infix),
        ("EQUALITY",      "OTHER = RESERVED", infix),
        ("EQUALITY",      "RESERVED = RESERVED", infix),
        ("EQUALITY_LIST", "EQUALITY;EQUALITY", infix),
        ("EQUALITY_LIST", "EQUALITY_LIST;EQUALITY", append_last),
        ("BOOL",          "RESERVED written as OTHER", infix),
        ("BOOL",          "RESERVED written as RESERVED", infix),
        ("BOOL",          "RESERVED written as EQUALITY_LIST", infix),
        ("BOOL",          "EQUALITY where OTHER", infix),
        ("OTHER",         "RESERVED OTHER", join),
        ("OTHER",         "OTHER RESERVED", join),
        ("OTHER",         "RESERVED RESERVED", infix),
    ]

    return SLR_Parser(token_list, productions, start_symbol, end_symbol, null_symbol)

if __name__ == "__main__":
    test_criteria = [
        "a = b",
        "response = b",
        "a = response",
        "response = answer",
        "response = b*answer",
        "response = q where q = a*b",
        "response = q+p where q = a*b; p = b*c",
        "response written as answer",
        "response written as a*b*c",
    ]
    reserved_expressions = {
        "learner":
            {"response": "a*b*c",},
        "task":
            {"answer": "c*b*a",}
    }
    criteria_parser = generate_criteria_parser(reserved_expressions)
    for criteria in test_criteria:
        tokens = criteria_parser.scan(criteria)
        print(tokens)
        tree = criteria_parser.parse(tokens)
        print(tree)
        print("---------------------------------------------------")