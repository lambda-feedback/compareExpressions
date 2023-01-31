# -------
# IMPORTS
# -------

from enum import Enum
import re
try:
    from slr_parsing_utilities import SLR_Parser, relabel, catch_undefined, infix, create_node
except ImportError:
    from .slr_parsing_utilities import SLR_Parser, relabel, catch_undefined, infix, create_node


# ---------
# FUNCTIONS
# ---------

def SLR_costum_comparison(expression_string,nodes=[],infix_operators=[],undefined=None,null=None,expression_node=None,start=None,end=None):
    expression_string = expression_string.strip()

    infix_operators_dictionary = dict()
    unique_infix_operator_symbols = []
    for (symbol,label) in infix_operators:
        if label in infix_operators_dictionary.keys():
            infix_operators_dictionary[label] += [symbol]
        else:
            unique_infix_operator_symbols += [symbol]
            infix_operators_dictionary.update({label: [symbol]})
    infix_operators_token = []
    for (label,symbols) in infix_operators_dictionary.items():
        infix_operators_token.append(((" *("+"|".join([re.escape(s) for s in symbols])+") *"),label))

    if undefined == None:
        undefined_symbol="UNDEFINED"
        undefined = (undefined_symbol, undefined_symbol, catch_undefined)
    else:
        undefined += (catch_undefined,)

    if null == None:
        null_symbol = "NULL"
        null = (null_symbol, null_symbol)

    if expression_node == None:
        expression_node_symbol="EXPRESSION_NODE"
        expression_node = (expression_node_symbol, expression_node_symbol, None)

    if start == None:
        start_symbol = "START"
        start = (start_symbol, start_symbol)

    if end == None:
        end_symbol = "END"
        end = (end_symbol, end_symbol)

    token_list = [undefined,null,expression_node,start,end]+nodes+infix_operators_token

    productions = [( start[0], expression_node[0], relabel )]
    productions += [( expression_node[0], n[0], create_node ) for n in nodes]
    productions += [( expression_node[0], undefined[0], create_node )]
    productions += [( expression_node[0], expression_node[0]+operator+expression_node[0], infix ) for operator in [op[0] for op in unique_infix_operator_symbols]]

    parser = SLR_Parser(token_list,productions,start[1],end[1],null[1])
    tokens = parser.scan(expression_string)

    #print(tokens)
    #for k in range(0,len(parser._states_index)/2):
    #    print(str(k)+": "+str(parser._states_index[k])+"\n")
    #print(parser.parsing_table_to_string())
    syntax_tree = parser.parse(tokens,verbose=False)

    return syntax_tree

def SLR_polynomial_parsing(expr):
    expr = expr.strip()

    # regexp from https://slavik.meltser.info/validate-number-with-regular-expression/
    # Non-negative integers
    is_integer = lambda string: string if re.fullmatch('^(0|[1-9]\d*)$',string) != None else None

    tokens = Enum("EnumsToken",{v:i for i,v in enumerate(["VARIABLE","NN_INTEGER","PLUS","MINUS","PRODUCT","POWER","OTHER","EXPRESSION_NODE"],1)})

    nodes = [
        ("x", tokens.VARIABLE) ,\
        ("N", tokens.NN_INTEGER,is_integer)
    ]

    infix_operators = [
        ("+", tokens.PLUS   ) ,\
        ("-", tokens.MINUS  ) ,\
        ("*", tokens.PRODUCT) ,\
        ("^", tokens.POWER  ) ,\
        ("**",tokens.POWER  )
    ]

    polynomial = SLR_costum_comparison(expr,nodes=nodes,infix_operators=infix_operators)

    if len(polynomial) > 1:
        print(polynomial)
        raise Exception("Parsed expression does not have a single root.")
    else:
        polynomial = polynomial[0]

    def extract_degree(monomial):
        if monomial.label == tokens.POWER \
           and monomial.children[0].label == tokens.VARIABLE \
           and monomial.children[1].label == tokens.NN_INTEGER:
            return int(monomial.children[1].content)
        elif monomial.label == tokens.VARIABLE:
            return 1
        else:
            return None

    def extract_degrees_and_coefficients(poly,coeffs):
        if poly.label == tokens.PLUS:
            for child in poly.children:
                if child.label == tokens.VARIABLE:
                    coeffs.append((1,'1'))
                elif child.label == tokens.NN_INTEGER:
                    coeffs.append((0,child.content))
                else:
                    extract_degrees_and_coefficients(child,coeffs)
        elif poly.label == tokens.MINUS:
            if poly.children[0].label == tokens.VARIABLE:
                coeffs.append((1,'1'))
            elif poly.children[0].label == tokens.NN_INTEGER:
                coeffs.append((0,poly.children[0].content))
            else:
                extract_degrees_and_coefficients(poly.children[0],coeffs)
            if poly.children[1].label == tokens.VARIABLE:
                coeffs.append((1,'-1'))
            elif poly.children[1].label == tokens.NN_INTEGER:
                coeffs.append((0,'-1*'+poly.children[1].content))
            else:
                extract_degrees_and_coefficients(poly.children[1],coeffs)
        elif poly.label == tokens.POWER:
            coeffs.append((extract_degree(poly),'1'))
        elif poly.label == tokens.PRODUCT \
             and poly.children[0].label in [tokens.NN_INTEGER,tokens.OTHER] \
             and poly.children[1].label in [tokens.POWER,tokens.VARIABLE]:
            coeffs.append((extract_degree(poly.children[1]),poly.children[0].content))
        return

    def get_polynomial_coefficient_list(poly):
        extracted_coeffs = []
        extract_degrees_and_coefficients(polynomial,extracted_coeffs)
        degree = max(x[0] for x in extracted_coeffs)
        coeffs = [[] for _ in range(degree+1)]
        for (term_degree,term_coeff) in extracted_coeffs:
            coeffs[term_degree] += [term_coeff]
        for k in range(degree+1):
            if len(coeffs[k]) > 0:
                coeffs[k] = "("+")+(".join(coeffs[k])+")"
            else:
                coeffs[k] = '0'
        return coeffs

    coeffs = get_polynomial_coefficient_list(polynomial)

    return polynomial, coeffs

# -----
# TESTS
# -----
if __name__ == "__main__":
    exprs = [
        "x+2",
        "2-x",
        "x-2",
        "x^2+1",
        "x^2+x+1",
        "x^3-3*x^2+1",
    ]

    for k, expr in enumerate(exprs):
        mid = "**  "+str(k)+": "+expr+"  **"
        print("*"*len(mid))
        print(mid)
        print("*"*len(mid))
        (polynomial,coeff) = SLR_polynomial_parsing(expr)
        print("Content: "+polynomial.content_string())
        #messages = [x[1] for x in quantity.messages]
        #for criteria_tag in quantity.passed_dict:
        #    messages += [criteria.feedbacks[criteria_tag](criteria.results[criteria_tag](quantity))]
        #print("\n".join(messages))
        print(polynomial.tree_string())
    print("** COMPLETE **")