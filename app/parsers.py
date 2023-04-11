from app.slr_parsing_utilities import SLR_expression_parser, compose, group, infix


def SLR_implicit_multiplication_convention_parser(convention):
    delimiters = [
        (("(", ")"), group(1))
    ]

    costum_tokens = [
        (" *(\*|\+|-| ) *", "SPLIT"), (" */ *", "SOLIDUS")
    ]

    infix_operators = []
    costum_productions = [("E", "*E", group(2, empty=True)),("E", "EE", group(2, empty=True))]
    if convention == "equal_precedence":
        costum_productions += [("E", "E/E", infix)]
    elif convention == "implicit_higher_precedence":
        costum_productions += [("E", "E/E", compose(infix, group(1, empty=True, delimiters=["(", ")"])))]
    else:
        raise Exception(f"Unknown convention {convention}")

    undefined = ("O", "OTHER")
    expression_node = ("E", "EXPRESSION_NODE")
    return SLR_expression_parser(delimiters=delimiters, infix_operators=infix_operators, undefined=undefined, expression_node=expression_node, costum_tokens=costum_tokens, costum_productions=costum_productions)
