from symbolic_equal import evaluation_function as symbolicEqual
from slr_parsing_utilities import SLR_expression_parser, compose, group, infix


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


def symbolic_comparison(response, answer, parameters):
    convention = parameters.get("convention", None)
    if convention is not None:
        parser = SLR_implicit_multiplication_convention_parser(convention)
        response = parser.parse(parser.scan(response))[0].content_string()
        answer = parser.parse(parser.scan(answer))[0].content_string()
    value_comparison_response = symbolicEqual(response, answer, parameters)
    return value_comparison_response


def compute_relative_tolerance_from_significant_decimals(string):
    rtol = None
    string = string.strip()
    separators = "e*^ "
    separator_indices = []
    for separator in separators:
        if separator in string:
            separator_indices.append(string.index(separator))
        else:
            separator_indices.append(len(string))
    index = min(separator_indices)
    significant_characters = string[0:index].replace(".", "")
    index = 0
    for c in significant_characters:
        if c in "-0":
            index += 1
        else:
            break
    significant_characters = significant_characters[index:]
    rtol = 5*10**(-len(significant_characters))
    return rtol