from lambdafeedback.slr_parsing import CatchAll, Lexeme, SLRParser, TokenPattern, create_node, infix, operate


def generate_criteria_parser(reserved_expressions):
    start_symbol = "START"
    end_symbol = "END"
    null_symbol = "NULL"

    criteria_operations = {
        "matches",
        "dimension",
        "=",
        "<=",
        ">=",
        "<",
        ">",
    }

    token_list = [
        TokenPattern(start_symbol, start_symbol),
        TokenPattern(end_symbol, end_symbol),
        TokenPattern(null_symbol, null_symbol),
        TokenPattern(Lexeme(("BOOL",), space_before=True, space_after=True), "BOOL"),
        TokenPattern(Lexeme(("QUANTITY",), space_before=True, space_after=True), "QUANTITY"),
        TokenPattern(Lexeme(("DIMENSION",), space_before=True, space_after=True), "DIMENSION"),
        TokenPattern(Lexeme(("(",), space_after=True), "START_DELIMITER"),
        TokenPattern(Lexeme((")",), space_before=True), "END_DELIMITER"),
        TokenPattern("response", "QUANTITY"),
        TokenPattern("answer", "QUANTITY"),
        CatchAll("INPUT", "INPUT"),
    ]
    token_list += [TokenPattern(Lexeme((x,), space_before=True, space_after=True), " "+x+" ") for x in criteria_operations]

    productions = [
        ("START",     "BOOL", create_node),
        ("BOOL",      "QUANTITY matches QUANTITY", infix),
        ("BOOL",      "DIMENSION matches DIMENSION", infix),
        ("BOOL",      "QUANTITY=QUANTITY", infix),
        ("BOOL",      "QUANTITY<=QUANTITY", infix),
        ("BOOL",      "QUANTITY>=QUANTITY", infix),
        ("BOOL",      "QUANTITY<QUANTITY", infix),
        ("BOOL",      "QUANTITY>QUANTITY", infix),
        ("QUANTITY",  "INPUT", create_node),
        ("DIMENSION", "dimension(QUANTITY)", operate(1)),
    ]

    return SLRParser(token_list, productions, start_symbol, end_symbol, null_symbol)
