from sympy.parsing.sympy_parser import parse_expr
from sympy.parsing.sympy_parser import T as parser_transformations
from sympy import latex

try:
    from .static_unit_conversion_arrays import list_of_SI_base_unit_dimensions, list_of_SI_prefixes
    from .expression_utilities import expression_to_latex
except ImportError:
    from static_unit_conversion_arrays import list_of_SI_base_unit_dimensions, list_of_SI_prefixes
    from expression_utilities import expression_to_latex

# -------------------
# GLOBALS DEFINITIONS
# -------------------
criteria = {}
add_criterion = lambda tag,test,output,feedback: criteria.update({tag: (test,output,feedback)})
test_criterion = lambda tag, tokens: criteria[tag][0](tokens)
criterion_output = lambda tag, tokens: criteria[tag][1](tokens)
criterion_feedback = lambda tag: criteria[tag][2]
types = lambda tokens: [x.type for x in tokens]
add_criterion("FULL_QUANTITY",\
    lambda tokens: types(tokens) in [["NON_UNIT","SPACE","UNIT_EXPR"],["NUMBER","SPACE","UNIT_EXPR"]],\
    lambda tokens: tokens,\
    "")
add_criterion("HAS_UNIT",
    lambda tokens: tokens[-1].type == "UNIT_EXPR",\
    lambda tokens: tokens[-1].content,\
    "Quantity has unit(s).")
add_criterion("ONLY_UNIT",
    lambda tokens: types(tokens) == ["UNIT_EXPR"],\
    lambda tokens: tokens[0].content,\
    "Quantity only has unit(s).")
add_criterion("NO_UNIT",
    lambda tokens: types(tokens) == ["NON_UNIT"],\
    lambda tokens: None,\
    "Quantity has no unit(s).")
add_criterion("HAS_VALUE",\
    lambda tokens: tokens[0].type in ["NON_UNIT","NUMBER"],\
    lambda tokens: tokens[0].content,\
    "Quantity has value.")
add_criterion("NO_VALUE",\
    lambda tokens: "NON_UNIT" not in types(tokens) and "NUMBER" not in types(tokens),\
    lambda tokens: None,\
    "Quantity has value.")
add_criterion("NUMBER_VALUE",\
    lambda tokens: types(tokens) == ["NUMBER","SPACE","UNIT_EXPR"] or types(tokens) == ["NUMBER"],\
    lambda tokens: tokens[0].content,\
    "Value is a number.")
add_criterion("EXPR_VALUE",\
    lambda tokens: types(tokens) == ["NON_UNIT","SPACE","UNIT_EXPR"] or types(tokens) == ["NON_UNIT"],\
    lambda tokens: tokens[0].content,\
    "Value is an expression.")

# -----------------
# CLASS DEFINITIONS
# -----------------
class Token:

    def __init__(self,type,content,original,start,end):
        self.type = type
        self.content = content
        self.original = original
        self.start = start
        self.end = end
        return

    def set_content(self,content):
        self.content = content

class Quantity:

    def __init__(self,tokens,messages):
        self.tokens = tokens
        self.passed_criteria = []
        self.messages = messages
        for criterion in criteria.keys():
            if test_criterion(criterion,tokens):
                self.passed_criteria += [criterion]
        return

    def passed(self,criterion):
        return criterion in self.passed_criteria

    def feedback(self,criterion):
        if self.passed(criterion):
            return criterion_feedback(criterion)
        else:
            return None

    def value(self):
        value = criterion_output("HAS_VALUE",self.tokens) if self.passed("HAS_VALUE") else None
        return value

    def unit(self):
        if self.passed("HAS_UNIT"):
            unit = criterion_output("HAS_UNIT",self.tokens)
            unit = "".join([x.content for x in unit])
        else:
            unit = None
        return unit

    def unit_tokens(self):
        if self.passed("HAS_UNIT"):
            unit = []
            for token in criterion_output("HAS_UNIT",self.tokens):
                unit.append(Token(token.type,token.content,token.original,token.start,token.end))
        else:
            unit = None
        return unit

    def print_string(self):
        string = []
        if self.passed("HAS_VALUE"):
            string += [criterion_output("HAS_VALUE",self.tokens)]
        if self.passed("HAS_UNIT"):
            string += [x.content for x in criterion_output("HAS_VALUE",self.tokens)]
        return "".join(string)

    def print_latex(self):
        expr = self.tokens[0].original
        latex = ""
        if self.passed("HAS_VALUE"):
            latex += criterion_output("HAS_VALUE",self.tokens)
        if len(latex) > 0:
            latex += "~"
        if self.passed("HAS_UNIT"):
            tokens = criterion_output("HAS_UNIT",self.tokens)
            tokens = tokens+[Token("END","",expr,tokens[-1].end+1,tokens[-1].end+1)]
            #tokens = tokens+[Token("END","",expr,0,0)]

            latex_substitutions = {"PRODUCT"         : lambda x: "\\cdot",\
                                   "NUMBER"          : lambda x: x,\
                                   "SPACE"           : lambda x: "~",\
                                   "PREFIX"          : lambda x: "\\mathrm{"+x+"}",\
                                   "UNIT"            : lambda x: "\\mathrm{"+x+"}",\
                                   "START_DELIMITER" : lambda x: x,\
                                   "END_DELIMITER"   : lambda x: x,\
                                   "EXPONENT"        : lambda x: "^",\
                                   "SOLIDUS"         : lambda x: "}{",\
                                   "LATEX"           : lambda x: x,\
                                   "END"             : lambda x: "",\
                                  }

            latex_consume_right = ["PRODUCT" ,"NUMBER", "SPACE", "UNIT","LATEX","END"]

            extend = lambda t, handle, prefix, suffix:\
                Token(t,prefix+handle[0].content+suffix,expr,handle[0].start,handle[0].end)
            substitute = lambda t, handle, substitutions:\
                Token(t,substitutions[handle[0].type](handle[0].content),expr,handle[0].start,handle[0].end)
            substitute_and_append = lambda t, handle, substitutions:\
                Token(t,handle[0].content+"".join([substitutions[x.type](x.content) for x in handle[1:]]),expr,handle[0].start,handle[-1].end)
            extend_substitute_and_append = lambda t, handle, prefix, suffix, substitutions:\
                Token(t,prefix+handle[0].content+"".join([substitutions[x.type](x.content) for x in handle[1:]])+suffix,expr,handle[0].start,handle[-1].end)

            reductions = \
                {("SPACE",)                                                     : lambda handle: substitute("LATEX",handle,latex_substitutions),\
                 ("NUMBER",)                                                    : lambda handle: substitute("LATEX",handle,latex_substitutions),\
                 ("PREFIX",)                                                    : lambda handle: substitute("LATEX",handle,latex_substitutions),\
                 ("UNIT",)                                                      : lambda handle: substitute("LATEX",handle,latex_substitutions),\
                 ("LATEX","EXPONENT","START_DELIMITER","LATEX","END_DELIMITER") : lambda handle: (handle[2].set_content("{"),handle[4].set_content("}"),substitute_and_append("LATEX",handle,latex_substitutions))[-1],\
                 ("LATEX","EXPONENT","NUMBER")                                  : lambda handle: substitute_and_append("LATEX",handle,latex_substitutions),\
                 ("LATEX","SOLIDUS","LATEX","SPACE")                            : lambda handle: extend_substitute_and_append("LATEX",handle,"\\frac{","}",latex_substitutions),\
                 ("LATEX","SOLIDUS","LATEX","END")                              : lambda handle: extend_substitute_and_append("LATEX",handle,"\\frac{","}",latex_substitutions),\
                 ("LATEX","SOLIDUS","START_DELIMITER","LATEX","END_DELIMITER")  : lambda handle: (handle[2].set_content("{"),handle[4].set_content("}"),extend_substitute_and_append("LATEX",handle,"\\frac{","}",latex_substitutions))[-1],\
                 ("START_DELIMITER","LATEX","END_DELIMITER")                    : lambda handle: substitute_and_append("LATEX",handle,latex_substitutions),\
                **{ ("LATEX",x)                                                 : lambda handle: substitute_and_append("LATEX",handle,latex_substitutions) for x in latex_consume_right },\
                }

            stack = parse(tokens,reductions)

            if len(stack) > 1:
                return "`"+self.tokens[0].original+"` could not be parsed as a valid unit expression."

            latex += stack[0].content

        return latex

# -----------------
# PARSING FUNCTIONS
# -----------------

def generate_unit_dictionary():
    base_units = {x[0]: x[0] for x in list_of_SI_base_unit_dimensions}
    base_units_short = {x[1]: x[0] for x in list_of_SI_base_unit_dimensions}
    prefixes = {x[0]: x[0] for x in list_of_SI_prefixes}
    prefixes_short = {x[1]: x[0] for x in list_of_SI_prefixes}
    units = base_units
    units_short = base_units_short
    units_tokens = {}
    for unit in units.keys():
        units_tokens.update({unit: lambda original,start,end,u=unit: [Token("UNIT",u,original,start,end)]})
    for unit in units_short.keys():
        units_tokens.update({unit: lambda original,start,end,u=unit: [Token("UNIT",units_short[u],original,start,end)]})
    prefixed_units_tokens = {}
    for prefix in prefixes.keys():
        for unit in units.keys():
            prefixed_units_tokens.update(\
                {prefix+unit: lambda original,start,end,p=prefix,u=unit:\
                                [Token("PREFIX",p+"",original,start,end),\
                                 Token("UNIT",u+"",original,start,end)]})
    for prefix in prefixes_short.keys():
        for unit in units_short.keys():
            prefixed_units_tokens.update(\
                {prefix+unit: lambda original,start,end,p=prefix,u=unit:\
                                [Token("PREFIX",prefixes_short[p]+"",original,start,start+len(p)),\
                                 Token("UNIT",  units_short[u]+"",original,end-(len(u))+1,end)]})
    return {**units_tokens,**prefixed_units_tokens}

def scan(expr):
    unit_dictionary = generate_unit_dictionary()
    tokens = []
    separators = {" ": "SPACE", "*": "PRODUCT", "/": "SOLIDUS",\
                  "(": "START_DELIMITER", ")": "END_DELIMITER",\
                  "^": "EXPONENT", "**": "EXPONENT"}

    index = [0]
    new_token = lambda t,c,s,e:  (index.append(j),Token(t,c,expr,s,e))[-1]
    i = 0
    while i < len(expr):
        lexeme = ""
        defer = None
        start = i
        end = i-1
        for j in range(i,len(expr)):
            c = expr[j]
            if c.isdigit() or c in "-.":
                end = j-1
                lexeme = expr[i:j]
                defer = new_token("NUMBER",c,j,j)
                i += 1
                break
            elif c in separators.keys():
                end = j-1
                lexeme = expr[i:j]
                if c == "*" and j+1 < len(expr) and expr[j+1] == "*":
                    defer = new_token(separators["**"],"**",j,j+1)
                    i += 2
                else:
                    defer = new_token(separators[c],c,j,j)
                    i += 1
                break
            if j == len(expr)-1:
                lexeme = expr[i:]
                j = len(expr)
        if len(lexeme) > 0:
            unit = unit_dictionary.get(lexeme,None)
            if unit == None:
                tokens.append(new_token("NON_UNIT",lexeme,start,end))
            else:
                tokens += unit(expr,start,end)
        if defer != None:
            tokens.append(defer)
        i += len(lexeme)
    return tokens

def parse(tokens,reductions):
    stack = [tokens.pop(0)]
    max_reduction_length = max(len(x) for x in reductions.keys())
    stack_changed = True
    while stack_changed:
        stack_changed = False
        reduction = None
        for k in range(min(len(stack),max_reduction_length),0,-1):
            handle = tuple(stack[-k:])
            reduction = reductions.get(tuple(x.type for x in handle),None)
            if reduction != None:
                stack = stack[0:-k]
                stack.append(reduction(handle))
                stack_changed = True
                break
        if reduction == None and len(tokens) > 0:
            stack.append(tokens.pop(0))
            stack_changed = True

    return stack

def strict_SI_parsing(expr):
    expr = expr.strip()
    tokens = scan(expr)

    add_to_stack     = lambda i, handle: handle[i]
    handle_to_list   = lambda t, handle:\
        Token(t,[x for x in handle],expr,handle[0].start,handle[-1].end)
    handle_to_list_n = lambda n, t, handle:\
        Token(t,[x for x in handle[0:n]],expr,handle[0].start,handle[n].end)
    append_to_head   = lambda t, handle:\
        Token(t,handle[0].content+[x for x in handle[1:]],expr,handle[0].start,handle[-1].end)
    append_to_head_n = lambda n, t, handle:\
        Token(t,handle[0].content+[x for x in handle[1:n+1]],expr,handle[0].start,handle[n].end)
    append_to_end    = lambda t, handle:\
        Token(t,[x for x in handle[0:-1]]+handle[-1].content,expr,handle[0].start,handle[-1].end)
    join             = lambda t, handle:\
        Token(t,"".join([x.content for x in handle]),expr,handle[0].start,handle[-1].end)
    concatenate      = lambda t, handle:\
        Token(t,sum([x.content if isinstance(x.content,list) else [x] for x in handle],[]),expr,handle[0].start,handle[-1].end)

    separators = ["SPACE","PRODUCT","SOLIDUS"]
    delimiters = ["START_DELIMITER","END_DELIMITER"]

    non_units_consume_left = ["NON_UNIT","NUMBER","EXPONENT"]+separators+delimiters
    non_units_consume_right = non_units_consume_left.copy()
    non_units_consume_right.remove("SPACE")

    unit_expr_consume = ["PREFIX","NUMBER","EXPONENT"]+delimiters

    quantity_reductions = \
        {("NUMBER","SOLIDUS","UNIT")          : lambda handle: handle_to_list("UNIT_EXPR",handle) if handle[0].content == "1"\
                                                               else join("NON_UNIT",handle),\
         ("NUMBER","SOLIDUS","UNIT_EXPR")     : lambda handle: handle_to_list("UNIT_EXPR",handle) if handle[0].content == "1"\
                                                               else join("NON_UNIT",handle),\
         ("NUMBER","NUMBER")                  : lambda handle: join("NUMBER",handle),\
         **{ ("NON_UNIT",x)                   : lambda handle: join("NON_UNIT",handle)              for x in non_units_consume_right },\
         **{ (x,"NON_UNIT")                   : lambda handle: join("NON_UNIT",handle)              for x in non_units_consume_left  },\
         **{ ("NON_UNIT",x,"NON_UNIT")        : lambda handle: join("NON_UNIT",handle)              for x in separators              },\
         **{ ("UNIT_EXPR",x)                  : lambda handle: append_to_head("UNIT_EXPR",handle)   for x in unit_expr_consume       },\
         **{ (x,"UNIT_EXPR")                  : lambda handle: append_to_end("UNIT_EXPR",handle)    for x in unit_expr_consume       },\
         **{ ("UNIT",x)                       : lambda handle: handle_to_list("UNIT_EXPR",handle)   for x in unit_expr_consume       },\
         **{ (x,"UNIT")                       : lambda handle: handle_to_list("UNIT_EXPR",handle)   for x in unit_expr_consume       },\
         **{ ("UNIT",x,"UNIT")                : lambda handle: handle_to_list("UNIT_EXPR",handle)   for x in separators              },\
         **{ ("UNIT_EXPR",x,"UNIT")           : lambda handle: append_to_head("UNIT_EXPR",handle)   for x in separators              },\
         **{ ("UNIT_EXPR",x,"UNIT_EXPR")      : lambda handle: concatenate("UNIT_EXPR",handle)      for x in separators              },\
         **{ ("UNIT",x,"UNIT_EXPR")           : lambda handle: append_to_end("UNIT_EXPR",handle)    for x in separators              },\
         **{ ("UNIT_EXPR","EXPONENT",x)       : lambda handle: (append_to_head_n(1,"UNIT_EXPR",handle),\
                                                                add_to_stack(2,handle))[-1]         for x in separators              },\
         **{ ("UNIT","EXPONENT",x)            : lambda handle: (handle_to_list("UNIT_EXPR",handle),\
                                                                add_to_stack(2,handle))[-1]         for x in separators              },\
         **{ ("UNIT_EXPR","EXPONENT",x)       : lambda handle: append_to_head("UNIT_EXPR",handle)   for x in delimiters              },\
         **{ ("UNIT","EXPONENT",x)            : lambda handle: handle_to_list("UNIT_EXPR",handle)   for x in delimiters              },\
        }

    stack = parse(tokens,quantity_reductions)

    result = [("ERROR","error"),("ERROR","error")]
    messages = []

    types_in_stack = [x.type for x in stack]
    # If there are any UNIT tokens left in expression, change them to a UNIT_EXPR token
    # with a single subtoken to simplify further analysis
    while "UNIT" in types_in_stack:
        t = stack[types_in_stack.index("UNIT")]
        token = Token(t.type,t.content,t.original,t.start,t.end)
        stack[types_in_stack.index("UNIT")] = Token("UNIT_EXPR",[token],token.original,token.start,token.end)
        types_in_stack = [x.type for x in stack]

    # Compress everything except separated UNIT_EXPR at end of stack into a single NON_UNIT token
    if types_in_stack[-2:] == ["SPACE","UNIT_EXPR"]:
        non_unit_stack = stack[0:-2]
        unit_stack = stack[-2:]
    elif types_in_stack[-1] == "UNIT_EXPR":
        non_unit_stack = stack[0:-1]
        unit_stack = [stack[-1]]
    else:
        non_unit_stack = stack
        unit_stack = []

    # If expression ends with a separated unit expression then the rest of the expression should be collected into a NON_UNIT
    if len(non_unit_stack) > 0 and [x.type for x in non_unit_stack] not in [["NON_UNIT"],["NUMBER"]] :
        for k in filter(lambda k: non_unit_stack[k].type == "UNIT_EXPR",range(0,len(non_unit_stack))):
            if isinstance(non_unit_stack[k].content,str):
                original = non_unit_stack[k].content.original
                start = non_unit_stack[k].content.start
                end = non_unit_stack[k].content.end
                ambiguity = original[start:end+1]
            else:
                original = non_unit_stack[k].content[0].original
                start = non_unit_stack[k].content[0].start
                end = non_unit_stack[k].content[-1].end
                ambiguity = "".join([x.original[x.start:x.end+1] for x in non_unit_stack[k].content])
            messages.append("WARNING: Possible ambiguity: '<mark>"+ambiguity+"</mark>' was not interpreted as a unit in `"+original[:start]+"<mark>"+ambiguity+"</mark>"+original[end+1:]+"`")
        non_unit = []
        for token in non_unit_stack:
            appendage = token.content if isinstance(token.content,str) else "".join(x.content for x in token.content)
            non_unit.append(appendage)
        stack = [Token("NON_UNIT","".join(non_unit),expr,non_unit_stack[0].start,non_unit_stack[-1].end)]+unit_stack
        types_in_stack = [x.type for x in stack]

    quantity = Quantity(stack,messages)

    return quantity

# NEW VERSION USING parsing_utilities
#from parsing_utilities import SLR_Parser, leaf, infix, group
#
#def SLR_strict_SI_parsing(expr):
#    start_symbol = "START"
#    end_symbol = "END"
#    null_symbol = "NULL"
#
#    token_list = [
#        (start_symbol, "START"),\
#        ("N", "NUMBER"),\
#        ("U", "UNIT"),\
#        ("V", "NON-UNIT"),\
#        ("E", "UNIT_EXPR"),\
#        (" ", "SPACE"),\ 
#        ("*", "PRODUCT"),\
#        ("/", "SOLIDUS"),\
#        ("^", "EXPONENT"),\
#        ("**", "EXPONENT"),\
#        ("(", "START_DELIMITER"),\
#        (")", "END_DELIMITER"),\
#        (end_symbol,"END"),\
#        (null_symbol,"NULL")
#        ]
#
#    expr_components = [x[0] for x in token_list[1:5]]
#    infix_symbols = [x[0] for x in token_list[5:10]]
#
#    productions = \
#        [ ( start_symbol, x , leaf ) for x in expr_components]\
#        +[ ( "E", "N/U", absorb ), ( "E", "N/E", absorb ) ]
#
#    parser = SLR_Parser(token_list,productions,start_symbol,end_symbol,null_symbol)
#    return quantity, unit_expr

# -----
# TESTS
# -----
if __name__ == "__main__":
    exprs = ["(5.27*pi/sqrt(11) + 5*7)^(2+2.3) (kilogram megametre^2)/(fs^4 daA)",\
            "10 kilogram/(metre second^2)",\
            "10 kilogram*metre/second**2",\
            "-10.5 kg m/s^2",\
            "10 kilogram*metre*second**(-2)",\
            "(5.27*pi/sqrt(11) + 5*7)^(4.3) (kilogram megametre^2)/(fs^4 daA)",\
            "(5*27/11 + 5*7)^(2*3) (kilogram megametre^2)/(fs^4 daA)",\
            "(pi+10) kg*m/s^2",\
            "10*pi kilogram*metre/second^2",\
            "10 kilogram*metre/second^2",\
            "10 kilogram metre/second^2",\
            "10 kg*m/s^2",\
            " 10 kg m/s^2 ",\
            "10 gram/metresecond",\
            "10 1/s^2",\
            "10 second/gram + 5 gram*second + 7 ms + 5 gram/second",\
            "10 second/gram * 7 ms * 5 gram/second",\
            "q",\
            "10",\
            "1/s^2",\
            ]
    
    for expr in exprs:
        result = strict_SI_parsing(expr)
        output_string = "\n".join(result.messages)+"\n"+result.print_latex()
        print("**********************************************************\n"+output_string)