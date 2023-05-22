from sympy.parsing.sympy_parser import parse_expr, split_symbols_custom, _token_splittable
from sympy.parsing.sympy_parser import T as parser_transformations
from sympy import Basic, Expr, Symbol

from .slr_parsing_utilities import (
    SLR_expression_parser,
    infix,
    group,
    compose
)

from .feedback.symbolic_comparison import internal as symbolic_comparison_internal_messages

elementary_functions_names = [
    ('sin', []), ('sinc', []), ('csc', ['cosec']), ('cos', []), ('sec', []), ('tan', []), ('cot', ['cotan']),
    ('asin', ['arcsin']), ('acsc', ['arccsc', 'arccosec']), ('acos', ['arccos']), ('asec', ['arcsec']),
    ('atan', ['arctan']), ('acot', ['arccot', 'arccotan']), ('atan2', ['arctan2']),
    ('sinh', []), ('cosh', []), ('tanh', []), ('csch', ['cosech']), ('sech', []),
    ('asinh', ['arcsinh']), ('acosh', ['arccosh']), ('atanh', ['arctanh']),
    ('acsch', ['arccsch', 'arccosech']), ('asech', ['arcsech']),
    ('exp', ['Exp']), ('E', ['e']), ('log', []),
    ('sqrt', []), ('sign', []), ('Abs', ['abs']), ('Max', ['max']), ('Min', ['min']), ('arg', []), ('ceiling', ['ceil']), ('floor', [])
]
elementary_functions_names.sort(key=lambda x: -len(x))


# -------- String Manipulation Utilities
def create_expression_set(expr, params):
    expr_set = set()
    if "plus_minus" in params.keys():
        expr = expr.replace(params["plus_minus"], "plus_minus")

    if "minus_plus" in params.keys():
        expr = expr.replace(params["minus_plus"], "minus_plus")

    if ("plus_minus" in expr) or ("minus_plus" in expr):
        expr_set.add(expr.replace("plus_minus", "+").replace("minus_plus", "-"))
        expr_set.add(expr.replace("plus_minus", "-").replace("minus_plus", "+"))
    else:
        expr_set.add(expr)

    return list(expr_set)

def convert_absolute_notation(expr, name):
    """
    Accept || as another form of writing modulus of an expression. 
    Function makes the input parseable by SymPy, SymPy only accepts Abs()
    REMARK: this function cannot handle nested ||. It will attempt to pair
    each | with the closest | to the right and return a string with a warning
    if it detects an ambiguity.

    Parameters
    ----------
    expr : string
        Expression to convert, might have ||

    Returns
    -------
    expr : string
        converted response input
    """

    # positions of the || values
    n_expr = expr.count('|')
    if n_expr == 2:
        expr = list(expr)
        expr[expr.index("|")] = "Abs("
        expr[expr.index("|")] = ")"
        expr = "".join(expr)
    elif n_expr > 0:
        expr_start_abs_pos = []
        expr_end_abs_pos = []
        expr_ambiguous_abs_pos = []

        if expr[0] == "|":
            expr_start_abs_pos.append(0)
        for i in range(1,len(expr)-1):
            if expr[i] == "|":
                if (expr[i-1].isalnum() or expr[i-1] in "()[]{}") and not (expr[i+1].isalnum() or expr[i+1] in "()[]{}"):
                    expr_end_abs_pos.append(i)
                elif (expr[i+1].isalnum() or expr[i+1] in "()[]{}") and not (expr[i-1].isalnum() or expr[i-1] in "()[]{}"):
                    expr_start_abs_pos.append(i)
                else:
                    expr_ambiguous_abs_pos.append(i)
        if expr[-1] == "|":
            expr_end_abs_pos.append(len(expr)-1)
        expr = list(expr)
        for i in expr_start_abs_pos:
            expr[i] = "Abs("
        for i in expr_end_abs_pos:
            expr[i] = ")"
        k = 0
        prev_ambiguous = -1
        for i in expr_ambiguous_abs_pos:
            prev_start = -1
            for j in expr_start_abs_pos:
                if j < i:
                    prev_start = j
                else:
                    break
            prev_end = -1
            for j in expr_end_abs_pos:
                if j < i:
                    prev_end = j
                else:
                    break
            if max(prev_start,prev_end,prev_ambiguous) == prev_end:
                if expr[i-1].isalnum():
                    expr[i] = "*Abs("
                else:
                    expr[i] = "Abs("
            elif max(prev_start,prev_end,prev_ambiguous) == prev_ambiguous:
                if k % 2 == 0:
                    if expr[i-1].isalnum():
                        expr[i] = "*Abs("
                    else:
                        expr[i] = "Abs("
                else:
                    expr[i] = ")"
                k += 1
            else:
                expr[i] = ")"
            prev_ambiguous = i
        expr = "".join(expr)

    ambiguity_tag = "ABSOLUTE_VALUE_NOTATION_AMBIGUITY"
    remark = ""
    if n_expr > 2 and len(expr_ambiguous_abs_pos) > 0:
        remark = symbolic_comparison_internal_messages[ambiguity_tag](name)

    feedback = None
    if len(remark) > 0:
        feedback = (ambiguity_tag, remark)

    return expr, feedback

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


def preprocess_according_to_chosen_convention(expression, parameters):
    convention = parameters.get("convention", None)
    if convention is not None:
        parser = SLR_implicit_multiplication_convention_parser(convention)
        expression = parser.parse(parser.scan(expression))[0].content_string()
    return expression

def substitute_input_symbols(exprs, params):
    '''
    Input:
        exprs  : a string or a list of strings
        params : Evaluation function parameter dictionary
    Output:
        List of strings where alternatives for input symbols have been replaced with
        their corresponsing input symbol code.
    Remark:
        Alternatives are sorted before substitution so that longer alternatives takes precedence.
    '''
    if isinstance(exprs, str):
        exprs = [exprs]

    if "input_symbols" in params.keys():
        input_symbols = params["input_symbols"]
        input_symbols_to_remove = []
        alternatives_to_remove = []
        for k in range(0, len(input_symbols)):
            if len(input_symbols[k]) > 0:
                input_symbols[k][0].strip()
                if len(input_symbols[k][0]) == 0:
                    input_symbols_to_remove += [k]
            else:
                for i in range(0, len(input_symbols[k][1])):
                    if len(input_symbols[k][1][i]) > 0:
                        input_symbols[k][1][i].strip()
                    if len(input_symbols[k][1][i]) == 0:
                        alternatives_to_remove += [(k, i)]
        for (k, i) in alternatives_to_remove:
            del input_symbols[k][1][i]
        for k in input_symbols_to_remove:
            del input_symbols[k]
        substitutions = []
        for input_symbol in params["input_symbols"]:
            substitutions.append((input_symbol[0], input_symbol[0]))
            for alternative in input_symbol[1]:
                if len(alternative) > 0:
                    substitutions.append((alternative, input_symbol[0]))
        substitutions.sort(key=lambda x: -len(x[0]))

        for k in range(0, len(exprs)):
            exprs[k] = substitute(exprs[k], substitutions)

    return exprs

def find_matching_parenthesis(string,index):
    depth = 0
    for k in range(index,len(string)):
        if string[k] == '(':
            depth += 1
            continue
        if string[k] == ')':
            depth += -1
            if depth == 0:
                return k
    return -1

def substitute(string, substitutions):
    '''
    Input:
        string        (required) : a string or a list of strings
        substitutions (required) : a list with elements of the form (string,string)
                                   or ((string,list of strings),string)
    Output:
        A string that is the input string where any occurence of the left element
        of each pair in substitutions have been replaced with the corresponding right element.
        If the first element in the substitution is of the form (string,list of strings) then the substitution will only happen if the first element followed by one of the strings in the list in the second element.
    Remarks:
        Substitutions are made in the input order but if a substitutions left element is a
        substring of a preceding substitutions right element there will be no substitution.
        In most cases it is good practice to sort the substitutions by the length of the left
        element in descending order.
        Examples:
            substitute("abc bc c", [("abc","p"), ("bc","q"), ("c","r")])
            returns: "p q r"
            substitute("abc bc c", [("c","r"), ("bc","q"), ("abc","p")])
            returns: "abr br r"
            substitute("p bc c", [("p","abc"), ("bc","q"), ("c","r")])
            returns: "abc q c"
            substitute("p bc c", [("c","r"), ("bc","q"), ("p","abc")])
            returns: "abc br r"
    '''
    if isinstance(string, str):
        string = [string]

    # Perform substitutions
    new_string = []
    for part in string:
        if not isinstance(part, str):
            new_string.append(part)
        else:
            index = 0
            string_buffer = ""
            while index < len(part):
                matched_start = False
                for k, pair in enumerate(substitutions):
                    if isinstance(pair[0], tuple):
                        match = False
                        for look_ahead in pair[0][1]:
                            if part.startswith(pair[0][0]+look_ahead, index):
                                match = True
                                break
                        substitution_length = len(pair[0][0])
                    else:
                        match = part.startswith(pair[0], index)
                        substitution_length = len(pair[0])
                    if match:
                        matched_start = True
                        if len(string_buffer) > 0:
                            new_string.append(string_buffer)
                            string_buffer = ""
                        new_string.append(k)
                        index += substitution_length
                        break
                if not matched_start:
                    string_buffer += part[index]
                    index += 1
            if len(string_buffer) > 0:
                new_string.append(string_buffer)

    for k, elem in enumerate(new_string):
        if isinstance(elem, int):
            new_string[k] = substitutions[elem][1]

    return "".join(new_string)

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

# -------- (Sympy) Expression Parsing Utilities
def create_sympy_parsing_params(params, unsplittable_symbols=tuple()):
    '''
    Input:
        params               : evaluation function parameter dictionary
        unsplittable_symbols : list of strings that will not be split when parsing
                               even if implicit multiplication is used.
    Output:
        parsing_params: A dictionary that contains necessary info for the
                        parse_expression function.
    '''

    if "input_symbols" in params.keys():
        to_keep = []
        for symbol in [x[0] for x in params["input_symbols"]]:
            if len(symbol) > 1:
                to_keep.append(symbol)
        unsplittable_symbols += tuple(to_keep)

    if params.get("specialFunctions", False) is True:
        from sympy import beta, gamma, zeta
    else:
        beta = Symbol("beta")
        gamma = Symbol("gamma")
        zeta = Symbol("zeta")
    if params.get("complexNumbers", False) is True:
        from sympy import I
    else:
        I = Symbol("I")
    if params.get("elementary_functions", False) is True:
        from sympy import E
        e = E
    else:
        E = Symbol("E")
    N = Symbol("N")
    O = Symbol("O")
    Q = Symbol("Q")
    S = Symbol("S")
    symbol_dict = {
        "beta": beta,
        "gamma": gamma,
        "zeta": zeta,
        "I": I,
        "N": N,
        "O": O,
        "Q": Q,
        "S": S,
        "E": E
    }

    for symbol in unsplittable_symbols:
        symbol_dict.update({symbol: Symbol(symbol)})

    strict_syntax = params.get("strict_syntax", True)

    parsing_params = {"unsplittable_symbols": unsplittable_symbols, "strict_syntax": strict_syntax, "symbol_dict": symbol_dict, "extra_transformations": tuple(), "elementary_functions": params.get("elementary_functions", False), "convention": params.get("convention", None)}

    return parsing_params


def parse_expression(expr, parsing_params):
    '''
    Input:
        expr           : string to be parsed into a sympy expression
        parsing_params : dictionary that contains parsing parameters
    Output:
        sympy expression created by parsing expr configured according
        to the parameters in parsing_params
    '''

    expr = preprocess_according_to_chosen_convention(expr, parsing_params)

    strict_syntax = parsing_params.get("strict_syntax", False)
    extra_transformations = parsing_params.get("extra_transformations", ())
    unsplittable_symbols = parsing_params.get("unsplittable_symbols", ())
    symbol_dict = parsing_params.get("symbol_dict", {})
    separate_unsplittable_symbols = [(x, " "+x+" ") for x in unsplittable_symbols]
    if parsing_params["elementary_functions"] is True:
        alias_substitutions = []
        for (name, alias) in elementary_functions_names:
            alias_substitutions += [(name, name)] + [(x, name) for x in alias]
        alias_substitutions.sort(key=lambda x: -len(x[0]))
        expr = substitute(expr, alias_substitutions)
        separate_unsplittable_symbols = [(x[0], " "+x[0]) for x in elementary_functions_names] + separate_unsplittable_symbols
        separate_unsplittable_symbols.sort(key=lambda x: -len(x[0]))
    expr = substitute(expr, separate_unsplittable_symbols)
    can_split = lambda x: False if x in unsplittable_symbols else _token_splittable(x)
    if strict_syntax:
        transformations = parser_transformations[0:4]+extra_transformations
    else:
        transformations = parser_transformations[0:4, 6]+extra_transformations+(split_symbols_custom(can_split),)+parser_transformations[8]
    if parsing_params.get("rationalise",False):
        transformations += parser_transformations[11]
    parsed_expr = parse_expr(expr, transformations=transformations, local_dict=symbol_dict, evaluate=False)
    if not isinstance(parsed_expr, Expr):
        parsed_expr = parse_expr(expr, transformations=transformations, local_dict=symbol_dict)
        if not isinstance(parsed_expr, Basic):
            raise ValueError(f"Failed to parse Sympy expression `{expr}`")
    return parsed_expr
