# -------
# IMPORTS
# -------

import re
try:
    from slr_parsing_utilities import SLR_Parser, relabel, catch_undefined, infix, create_node
except ImportError:
    from .slr_parsing_utilities import SLR_Parser, relabel, catch_undefined, infix, create_node


# ---------
# FUNCTIONS
# ---------

def SLR_polynomial_parsing(expr):
    expr = expr.strip()

    # regexp from https://slavik.meltser.info/validate-number-with-regular-expression/
    # Non-negative integers
    is_integer = lambda string: string if re.fullmatch('^(0|[1-9]\d*)$',string) != None else None

    start_symbol = "START"
    end_symbol = "END"
    null_symbol = "NULL"

    token_list = [
        (start_symbol, start_symbol       ) ,\
        (end_symbol,   end_symbol         ) ,\
        (null_symbol,  null_symbol        ) ,\
        (" *\* *",     "PRODUCT"          ) ,\
        (" *\+ *",     "PLUS"             ) ,\
        (" *- *",      "MINUS"            ) ,\
        (" *\^ *",     "POWER"            ) ,\
        (" *\*\* *",   "POWER"            ) ,\
        ("x",          "VARIABLE"         ) ,\
        ("N",          "NN_INTEGER",      is_integer) ,\
        ("O",          "OTHER",           catch_undefined) ,\
        ("E",          "EXPRESSION_NODE", None) ,\
    ]

    productions = [( start_symbol, "E" , relabel )]
    productions += [( "E", "O" , create_node )]
    productions += [( "E", "N" , create_node )]
    productions += [( "E", "x" , create_node )]
    productions += [( "E", "E"+x+"E", infix ) for x in list("-+*^")]

    parser = SLR_Parser(token_list,productions,start_symbol,end_symbol,null_symbol)
    tokens = parser.scan(expr)

    #print(tokens)
    #for k in range(0,len(parser._states_index)/2):
    #    print(str(k)+": "+str(parser._states_index[k])+"\n")
    #print(parser.parsing_table_to_string())
    polynomial = parser.parse(tokens,verbose=False)

    if len(polynomial) > 1:
        print(polynomial)
        raise Exception("Parsed expression does not have a single root.")
    else:
        polynomial = polynomial[0]

    def extract_degree(monomial):
        if monomial.label == "POWER" and monomial.children[0].label == "VARIABLE" and monomial.children[1].label == "NN_INTEGER":
            return int(monomial.children[1].content)
        elif monomial.label == "VARIABLE":
            return 1
        else:
            return None

    def extract_degrees_and_coefficients(poly,coeffs):
        if poly.label == "PLUS":
            for child in poly.children:
                if child.label == "VARIABLE":
                    coeffs.append((1,'1'))
                elif child.label == "NN_INTEGER":
                    coeffs.append((0,child.content))
                else:
                    extract_degrees_and_coefficients(child,coeffs)
        elif poly.label == "MINUS":
            if poly.children[0].label == "VARIABLE":
                coeffs.append((1,'1'))
            elif poly.children[0].label == "NN_INTEGER":
                coeffs.append((0,poly.children[0].content))
            else:
                extract_degrees_and_coefficients(poly.children[0],coeffs)
            if poly.children[1].label == "VARIABLE":
                coeffs.append((1,'-1'))
            elif poly.children[1].label == "NN_INTEGER":
                coeffs.append((0,'-1*'+poly.children[1].content))
            else:
                extract_degrees_and_coefficients(poly.children[1],coeffs)
        elif poly.label == "POWER":
            coeffs.append((extract_degree(poly),'1'))
        elif poly.label == "PRODUCT" and poly.children[0].label in ["NN_INTEGER","OTHER"] and poly.children[1].label in ["POWER","VARIABLE"]:
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
        polynomial = SLR_polynomial_parsing(expr)
        print("Content: "+polynomial.content_string())
        #messages = [x[1] for x in quantity.messages]
        #for criteria_tag in quantity.passed_dict:
        #    messages += [criteria.feedbacks[criteria_tag](criteria.results[criteria_tag](quantity))]
        #print("\n".join(messages))
        print(polynomial.tree_string())
    print("** COMPLETE **")