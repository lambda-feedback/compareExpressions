# -------
# IMPORTS
# -------

from enum import Enum
try:
    from expression_utilities import substitute
    from slr_parsing_utilities import SLR_Parser, relabel, join, catch_undefined, infix, group, tag, tag_transfer, tag_removal, node, append, hidden
    from static_unit_conversion_arrays import list_of_SI_base_unit_dimensions, list_of_SI_prefixes, conversion_to_base_si_units_dictionary
except ImportError:
    from .expression_utilities import substitute
    from .slr_parsing_utilities import SLR_Parser, relabel, join, catch_undefined, infix, group, tag, tag_transfer, tag_removal, node, append, hidden
    from .static_unit_conversion_arrays import list_of_SI_base_unit_dimensions, list_of_SI_prefixes, conversion_to_base_si_units_dictionary


# -------
# CLASSES
# -------

QuantityTags = Enum("QuantityTags",{v:i for i,v in enumerate("UVN",1)})

class CriterionCollection:

    def __init__(self):
        self.tags = set()
        self.checks = dict()
        self.results = dict()
        self.feedbacks = dict()
        return

    def add_criterion(self,tag,check,result,feedback):
        if tag in self.tags:
            raise Exception("Criterion with tag: '"+str(tag)+"' already defined, use update_criterion to change criterion or choose a unique tag")
        else:
            self.tags.add(tag)
            self.checks.update({tag:check})
            self.results.update({tag:result})
            self.feedbacks.update({tag:feedback})
        return

    def update_criterion(self,tag,check,result,feedback):
        if tag not in self.tags:
            raise Exception("No criterion with tag: '"+str(tag)+"' defined.")
        else:
            self.checks.update({tag:check})
            self.results.update({tag:result})
            self.feedbacks.update({tag:feedback})
        return

criteria = CriterionCollection()

criteria.add_criterion("FULL_QUANTITY",\
    lambda x: x.value != None and x.unit != None,\
    lambda x: (x.value.content_string(),x.unit.content_string()),\
    lambda result: "Quantity has both value and unit.\nUnit: "+result[1]+"\nValue: "+result[0])
criteria.add_criterion("HAS_UNIT",\
    lambda x: x.unit != None,\
    lambda x: x.unit.content_string(),\
    lambda result: "Quantity has unit: "+result)
criteria.add_criterion("ONLY_UNIT",
    lambda x: x.value == None and x.unit != None,\
    lambda x: x.unit.content_string(),\
    lambda result: "Quantity has no value, only unit(s): "+result)
criteria.add_criterion("NO_UNIT",
    lambda x: x.unit == None,\
    lambda x: None,\
    lambda result: "Quantity has no unit.")
criteria.add_criterion("HAS_VALUE",\
    lambda x: x.value != None,\
    lambda x: x.value.content_string(),\
    lambda result: "Quantity has value: "+result)
criteria.add_criterion("NO_VALUE",\
    lambda x: x.value == None,\
    lambda x: None,\
    lambda result: "Quantity has no value.")
criteria.add_criterion("NUMBER_VALUE",\
    lambda x: x.value != None and x.value.tags == {QuantityTags.N},\
    lambda x: x.value.content_string(),\
    lambda result: "Value is a number: "+result)
criteria.add_criterion("EXPR_VALUE",\
    lambda x: x.value != None and QuantityTags.V in x.value.tags,\
    lambda x: x.value.content_string(),\
    lambda result: "Value is an expression: "+result)
criteria.add_criterion("REVERTED_UNIT",\
    lambda x: "REVERTED_UNIT" in [y[0] for y in x.messages],\
    lambda x: "\n".join([y[1] for y in x.messages if y[0]=="REVERTED_UNIT"]),\
    lambda result: "There were parsing ambiguities:\n"+result)


class PhysicalQuantity:

    def __init__(self,ast_root,messages):
        self.messages = messages
        self.ast_root = ast_root
        self.value = None
        self.unit = None
        self._rotations_performed = []
        self._rotate_until_root_is_split()
        if self.ast_root.label == "SPACE":
            self.value = self.ast_root.children[0]
            self.unit = self.ast_root.children[1]
        elif QuantityTags.U in self.ast_root.tags:
            self._undo_rotations()
            self.unit = self.ast_root
        else:
            self._undo_rotations()
            self.value = self.ast_root
        if self.value != None:
            def revert_content(node):
                if node.label != "GROUP":
                    node.content = node.original[node.start:node.end+1]
                if node.label == "UNIT":
                    self.messages += [("REVERTED_UNIT","WARNING: Possible ambiguity: '<mark>"+node.content+"</mark>' was not interpreted as a unit in `"+node.original[:node.start]+"<mark>"+node.content+"</mark>"+node.original[node.end+1:]+"`")]
                return ["",""]
            self.value.traverse(revert_content)
        self.passed_dict = dict()
        for tag in criteria.tags:
            if criteria.checks[tag](self):
                self.passed_dict.update({tag:criteria.feedbacks[tag](criteria.results[tag](self))})
        return

    def passed(self,tag):
        return self.passed_dict.get(tag,None)

    def _rotate(self,direction):
        # right: direction = 1
        # left: direction = 0
        if direction not in {0,1}:
            raise Exception("Unknown direction: "+str(direction))
        self._rotations_performed.append(direction)
        old_root = self.ast_root
        new_root = old_root.children[1-direction]
        if len(new_root.children) == 1:
            old_root.children = old_root.children[1-direction:len(old_root.children)-direction]
            a = [] if direction == 0 else [old_root]
            b = [old_root] if direction == 0 else []
            new_root.children = a+new_root.children+b
        elif len(new_root.children) > 1:
            switch = new_root.children[-direction]
            old_root.children[1-direction] = switch
            new_root.children[-direction] = old_root
        else:
            direction_string = "right" if direction == 1 else "left"
            raise Exception("Cannot rotate "+direction_string+".")
        # TODO: Use user defined operations for tag transfer instead
        for child in old_root.children:
            old_root.tags = old_root.tags | child.tags
            if QuantityTags.V in old_root.tags and QuantityTags.U in old_root.tags:
                old_root.tags.remove(QuantityTags.U)
        for child in old_root.children:
            new_root.tags = new_root.tags | child.tags
            if QuantityTags.V in new_root.tags and QuantityTags.U in new_root.tags:
                new_root.tags.remove(QuantityTags.U)
        self.ast_root = new_root
        return

    def _rotate_right(self):
        if len(self.ast_root.children) > 0:
            self._rotate(1)
        else:
            raise Exception("Cannot rotate right.")
        return

    def _rotate_left(self):
        if len(self.ast_root.children) > 0:
            self._rotate(0)
        else:
            raise Exception("Cannot rotate left.")
        return

    def _rotate_until_root_is_split(self):
        if self.ast_root.label in ["SPACE","HIDDEN"] :
            if QuantityTags.V in self.ast_root.children[1].tags:
                self._rotate_left()
                self._rotate_until_root_is_split()
            elif QuantityTags.U in self.ast_root.children[0].tags:
                self._rotate_right()
                self._rotate_until_root_is_split()
        return

    def _undo_rotations(self):
        while len(self._rotations_performed) > 0:
            self._rotate((self._rotations_performed[-1]+1) % 2)
            self._rotations_performed = self._rotations_performed[0:-2]
        return

# ---------
# FUNCTIONS
# ---------

def SLR_generate_unit_dictionary():
    base_units = {x[0]: x[0] for x in list_of_SI_base_unit_dimensions}
    base_units_short_to_long = {x[1]: x[0] for x in list_of_SI_base_unit_dimensions}
    base_units_long_to_short = {x[0]: x[1] for x in list_of_SI_base_unit_dimensions}
    prefixes = {x[0]: x[0] for x in list_of_SI_prefixes}
    prefixes_short_to_long = {x[1]: x[0] for x in list_of_SI_prefixes}
    prefixes_long_to_short = {x[0]: x[1] for x in list_of_SI_prefixes}
    units = base_units
    units_short_to_long = base_units_short_to_long
    units_long_to_short = base_units_long_to_short
    prefixed_units = {**units}
    for unit in units.keys():
        for prefix in prefixes.keys():
            prefixed_units.update(\
                {\
                    prefix+unit: prefix+unit,\
                    prefixes_long_to_short[prefix]+units_long_to_short[unit]: prefix+unit
                }\
            )
    return {**prefixed_units, **units, **units_short_to_long}

def SLR_strict_SI_parsing(expr):
    expr = expr.strip()
    unit_dictionary = SLR_generate_unit_dictionary()
    lookup_unit = lambda x: unit_dictionary.get(x,None)
    is_number = lambda string: string if all(c.isdigit() or c in "-." for c in string) else None

    start_symbol = "START"
    end_symbol = "END"
    null_symbol = "NULL"

    token_list = [
        (start_symbol, "START"           ) ,\
        (end_symbol,   "END"             ) ,\
        (null_symbol,  "NULL"            ) ,\
        (" ",          "SPACE"           ) ,\
        ("*",          "PRODUCT"         ) ,\
        ("/",          "SOLIDUS"         ) ,\
        ("^",          "POWER"           ) ,\
        ("**",         "POWER"           ) ,\
        ("(",          "START_DELIMITER" ) ,\
        (")",          "END_DELIMITER"   ) ,\
        ("N",          "NUMBER",         is_number) ,\
        ("U",          "UNIT",           lookup_unit) ,\
        ("V",          "NON-UNIT",       catch_undefined) ,\
        ("Q",          "QUANTITY_NODE",  None) ,\
        ]

    def transfer_tags_op(op):
        def apply(prod,out):
            return tag_removal(prod,tag_transfer(prod,op(prod,out)),QuantityTags.U,lambda x: QuantityTags.V in x)
        return apply

    def transfer_tags_infix(prod,out):
        out = tag_transfer(prod,infix(prod,out))
        node = out[-1]
        if node.label == "POWER" and QuantityTags.U in node.children[0].tags and node.children[1].tags == {QuantityTags.N}:
            out = tag_removal(prod,out,QuantityTags.N)
        elif node.label == "SOLIDUS" and node.children[0].content == "1" and node.children[1].tags == {QuantityTags.U}:
            out = tag_removal(prod,out,QuantityTags.N)
        elif node.label != "SPACE":
            out = tag_removal(prod,out,QuantityTags.U,lambda x: QuantityTags.N in x)
            out = tag(prod,out,QuantityTags.V,lambda x: QuantityTags.N in x)
        out = tag_removal(prod,out,QuantityTags.U,lambda x: QuantityTags.V in x)
        return out

    def tag_node(tag_value):
        def apply(prod,out):
            return tag(prod,node(prod,out),tag_value)
        return apply

    productions = [( start_symbol, "Q" , relabel )]
    #productions += [( "Q", "QQ" , transfer_tags_op(hidden) )]
    productions += [( "Q", "QQ" , transfer_tags_op(append) )]
    productions += [( "Q", "(Q)" , transfer_tags_op(group) )]
    productions += [( "Q", "U" , tag_node(QuantityTags.U) )]
    productions += [( "Q", "N" , tag_node(QuantityTags.N) )]
    productions += [( "Q", "V" , tag_node(QuantityTags.V) )]
    productions += [( "Q", "Q"+x+"Q", transfer_tags_infix ) for x in list(" */^")]

    #TODO: Change this so duplicate productions give an error instead of just being printed
    prods = []
    duplicate_error_string = []
    for prod in [(x[0],x[1]) for x in productions]:
        if prod in prods:
            duplicate_error_string.append(f"duplicate: {prod}")
        prods.append(prod)
    if len(duplicate_error_string) > 0:
        raise Exception("There are duplicate productions:\n"+"\n".join(duplicate_error_string))

    parser = SLR_Parser(token_list,productions,start_symbol,end_symbol,null_symbol)
    tokens = parser.scan(expr)

    rules = [( "N", "N"+x+"N", join ) for x in list("*/^")]
    rules += [( "V", "V(V)", join ), ( "V", "V(N)", join )]
    rules += [( "V", "NV", join ), ( "V", "VV", join )]
    rules += [( "V", "V N", join ), ( "V", " V", join )]
    rules += [( x, " "+x, join ) for x in list(" */^")] #\TODO: Try to rewrite as error handling
    rules += [( x, x+" ", join ) for x in list(" */^")] #\TODO: Try to rewrite as error handling
    #tokens = parser.process(tokens,rules)

    #TODO: Can we use state dictionary to get right marker from production?
    def error(stack,a,input_tokens,tokens,output,parser):
        last_token = output.pop()
        if last_token.label == "SPACE" and a.label in ["SPACE","PRODUCT","SOLIDUS","POWER"]:
            a.content = last_token.content + a.content
            output.append(a)
            a = tokens.pop(0)
        elif last_token.label in ["PRODUCT","SOLIDUS","POWER"] and a.label == "SPACE":
            last_token.content += a.content
            output.append(last_token)
            a = tokens.pop(0)
        return stack,a,input_tokens,tokens,output,parser

    #print(tokens)
    #print(parser.parsing_table_to_string())
    quantity = parser.parse(tokens,verbose=False,error_handler=error)

    if len(quantity) > 1:
        print(quantity)
        raise Exception("Parsed quantity does not have a single root.")

    quantity = PhysicalQuantity(quantity[0],[])

    def unit_latex(node):
        # TODO: skip unnecessary parenthesis (i.e. chech for GROUP children for powers and fraction and inside groups)
        content = node.content
        children = node.children
        if node.label == "PRODUCT":
            return unit_latex(children[0])+["\\cdot"]+unit_latex(children[1])
        elif node.label == "NUMBER":
            return [content]
        elif node.label == "SPACE":
            return unit_latex(children[0])+["~"]+unit_latex(children[1])
        elif node.label == "UNIT":
            return ["\\mathrm{"]+[content]+["}"]
        elif node.label == "GROUP":
            out = [content[0]]
            for child in children:
                out += unit_latex(child)
            return out+[content[1]]
        elif node.label == "POWER":
            return unit_latex(children[0])+["^{"]+unit_latex(children[1])+["}"]
        elif node.label == "SOLIDUS":
            return ["\\frac{"]+unit_latex(children[0])+["}{"]+unit_latex(children[1])+["}"]
        else:
            return [content]

    unit_latex_string = "".join(unit_latex(quantity.unit)) if quantity.unit != None else None

    return quantity, unit_latex_string

# -----
# TESTS
# -----
if __name__ == "__main__":
    exprs = [
        "q",
        "10",
        "-10.5*4",
        "pi*5",
        "5*pi",
        "sin(-10.5*4)",
        "kilogram/(metre second^2)",
        "10 kilogram/(metre second^2)",
        "10 kilogram*metre/second**2",
        "-10.5 kg m/s^2",
        "10 kilogram*metre*second**(-2)",
        "10*pi kilogram*metre/second^2",
        "(5.27*pi/sqrt(11) + 5*7)^(4.3)",
        "(kilogram megametre^2)/(fs^4 daA)",
        "(5.27*pi/sqrt(11) + 5*7)^(4.3) (kilogram megametre^2)/(fs^4 daA)",
        "(5.27*pi/sqrt(11) + 5*7)^(2+2.3) (kilogram megametre^2)/(fs^4 daA)",
        "(5*27/11 + 5*7)^(2*3) (kilogram megametre^2)/(fs^4 daA)",
        "(pi+10) kg*m/s^2",
        "10 kilogram*metre/second^2",
        "10 kg*m/s^2",
        " 10 kg m/s^2 ",
        "10 gram/metresecond",
        "10 s/g + 5 gram*second^2 + 7 ms + 5 gram/second^3",
        "10 second/gram * 7 ms * 5 gram/second",
        "pi+metre second+pi",
        "1/s^2",
        "5/s^2",
        "10 1/s^2",
        ]


    for k, expr in enumerate(exprs):
        mid = "**  "+str(k)+": "+expr+"  **"
        print("*"*len(mid))
        print(mid)
        print("*"*len(mid))
        quantity, unit_latex = SLR_strict_SI_parsing(expr)
        value = quantity.value.original_string() if quantity.value != None else None
        unit = quantity.unit.original_string() if quantity.unit != None else None
        print("Content: "+quantity.ast_root.content_string())
        print("Value:   "+str(value))
        print("Unit:    "+str(unit))
        print("LaTeX:   "+str(unit_latex))
        messages = [x[1] for x in quantity.messages]
        for criteria_tag in quantity.passed_dict:
            messages += [criteria.feedbacks[criteria_tag](criteria.results[criteria_tag](quantity))]
        print("\n".join(messages))
        print(quantity.ast_root.tree_string())
    print("** COMPLETE **")