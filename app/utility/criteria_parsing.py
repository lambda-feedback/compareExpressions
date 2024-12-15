from .slr_parsing_utilities import SLR_Parser, catch_undefined, infix, create_node, join, proceed, append_last

start_symbol = "START"
end_symbol = "END"
null_symbol = "NULL"

base_token_list = [
    (start_symbol, start_symbol),
    (end_symbol, end_symbol),
    (null_symbol, null_symbol),
    (" *BOOL *", "BOOL"),
    (" *EQUALITY *", "EQUALITY"),
    (" *EQUAL *", "EQUAL"),
    (" *EQUAL_LIST *", "EQUAL_LIST"),
    (" *RESERVED *", "RESERVED"),
    (" *= *", "EQUALITY"),
    (" *(>=?|<=?|ORDER) *", "ORDER"),  # less than (or equal), < (<=), greater than (or equal), > (>=)
    (" *where *", "WHERE"),
    (" *written as *", "WRITTEN_AS"),
    (" *; *", "SEPARATOR"),
    (" *OTHER *", "OTHER", catch_undefined),
]

base_productions = [
    ("START", "BOOL", create_node),
    ("BOOL", "EQUAL", proceed),
    ("BOOL", "ORDER", proceed),
    ("BOOL", "EQUAL where EQUAL", infix),
    ("BOOL", "EQUAL where EQUAL_LIST", infix),
    ("BOOL", "RESERVED written as OTHER", infix),
    ("BOOL", "RESERVED written as RESERVED", infix),
    ("EQUAL_LIST", "EQUAL;EQUAL", infix),
    ("EQUAL_LIST", "EQUAL_LIST;EQUAL", append_last),
    ("EQUAL", "OTHER = OTHER", infix),
    ("EQUAL", "RESERVED = OTHER", infix),
    ("EQUAL", "OTHER = RESERVED", infix),
    ("EQUAL", "RESERVED = RESERVED", infix),
    ("EQUAL", "OTHER ORDER OTHER", infix),
    ("EQUAL", "RESERVED ORDER OTHER", infix),
    ("EQUAL", "OTHER ORDER RESERVED", infix),
    ("EQUAL", "RESERVED ORDER RESERVED", infix),
    ("OTHER", "RESERVED OTHER", join),
    ("OTHER", "OTHER RESERVED", join),
    ("OTHER", "OTHER OTHER", join),
]


def generate_criteria_parser(reserved_expressions, token_list=base_token_list, productions=base_productions):

    for value in reserved_expressions.values():
        token_list += [(key, "RESERVED") for key in value.keys()]

    return SLR_Parser(token_list, productions, start_symbol, end_symbol, null_symbol)


if __name__ == "__main__":
    test_criteria = []
    for comparison in ["=", ">", "<", ">=", "<="]:
        test_criteria += [
            f"a {comparison} b",
            f"response {comparison} b",
            f"a {comparison} response",
            f"response {comparison} answer",
        ]
    test_criteria += [
        "response = b*answer",
        "response = q where q = a*b",
        "response = q+p where q = a*b; p = b*c",
        "response written as answer",
        "response written as a*b*c",
        "response - answer = 0",
    ]
    reserved_expressions = {
        "learner":
            {"response": "a*b*c", },
        "task":
            {"answer": "c*b*a", }
    }
    criteria_parser = generate_criteria_parser(reserved_expressions)
    for criteria in test_criteria:
        tokens = criteria_parser.scan(criteria)
        print(tokens)
        tree = criteria_parser.parse(tokens)
        print(tree)
        print("---------------------------------------------------")
