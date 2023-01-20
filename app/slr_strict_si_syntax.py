# -------
# IMPORTS
# -------

from enum import Enum
import re
try:
    from expression_utilities import substitute
    from criteria_utilities import CriterionCollection
    from slr_parsing_utilities import SLR_Parser, relabel, join, catch_undefined, infix, group, tag, tag_transfer, tag_removal, create_node, append
    from static_unit_conversion_arrays import list_of_SI_base_unit_dimensions, list_of_SI_prefixes, conversion_to_base_si_units_dictionary
except ImportError:
    from .expression_utilities import substitute
    from .criteria_utilities import CriterionCollection
    from .slr_parsing_utilities import SLR_Parser, relabel, join, catch_undefined, infix, group, tag, tag_transfer, tag_removal, create_node, append
    from .static_unit_conversion_arrays import list_of_SI_base_unit_dimensions, list_of_SI_prefixes, conversion_to_base_si_units_dictionary


# -------
# CLASSES
# -------

QuantityTags = Enum("QuantityTags",{v:i for i,v in enumerate("UVN",1)})

criteria = CriterionCollection()

criteria.add_criterion("FULL_QUANTITY",\
    lambda x: x.value != None and x.unit != None,\
    lambda x: (x.value.content_string(),x.unit.content_string()),\
    lambda result: "Quantity has both value and unit.<br>Value: "+result[0]+"<br>Unit: "+result[1])
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

    def __init__(self,ast_root,messages=[],tag_handler=lambda x: x):
        self.messages = messages
        self.ast_root = ast_root
        self.tag_handler = tag_handler
        self.value = None
        self.unit = None
        self._rotate_until_root_is_split()
        if self.ast_root.label == "SPACE"\
            and QuantityTags.U not in self.ast_root.children[0].tags\
            and QuantityTags.U in self.ast_root.children[1].tags:
            self.value = self.ast_root.children[0]
            self.unit = self.ast_root.children[1]
        elif QuantityTags.U in self.ast_root.tags:
            self.unit = self.ast_root
        else:
            self.value = self.ast_root
        if self.value != None:
            def revert_content(node):
                if node.label != "GROUP":
                    node.content = node.original[node.start:node.end+1]
                if node.label == "UNIT":
                    self.messages += [("REVERTED_UNIT","WARNING: Possible ambiguity: <strong>`"+node.content+"`</strong> was not interpreted as a unit in<br>`"+node.original[:node.start]+"`<strong>`"+node.content+"`</strong>`"+node.original[node.end+1:]+"`")]
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
        old_root = self.tag_handler(old_root)
        new_root = self.tag_handler(new_root)
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
        if self.ast_root.label == "SPACE":
            if QuantityTags.U not in self.ast_root.tags and len(self.ast_root.children[1].children) > 0:
                self._rotate_left()
                self._rotate_until_root_is_split()
            elif QuantityTags.U in self.ast_root.children[0].tags and len(self.ast_root.children[0].children) > 0:
                self._rotate_right()
                self._rotate_until_root_is_split()
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

    # regexp from https://slavik.meltser.info/validate-number-with-regular-expression/
    # see penultimate entry in section "Numbers with a Scientific Notation: Fractional numbers"
    is_number = lambda string: string if re.fullmatch('^-?(0|[1-9]\d*)?(\.\d+)?(?<=\d)(e-?(0|[1-9]\d*))?$',string) != None else None

    start_symbol = "START"
    end_symbol = "END"
    null_symbol = "NULL"

    token_list = [
        (start_symbol, start_symbol      ) ,\
        (end_symbol,   end_symbol        ) ,\
        (null_symbol,  null_symbol       ) ,\
        (" +",         "SPACE"           ) ,\
        (" *\* *",     "PRODUCT"         ) ,\
        (" */ *",      "SOLIDUS"         ) ,\
        (" *\^ *",     "POWER"           ) ,\
        (" *\*\* *",   "POWER"           ) ,\
        ("\( *",       "START_DELIMITER" ) ,\
        (" *\)",       "END_DELIMITER"   ) ,\
        ("N",          "NUMBER",         is_number) ,\
        ("U",          "UNIT",           lookup_unit) ,\
        ("V",          "NON-UNIT",       catch_undefined) ,\
        ("Q",          "QUANTITY_NODE",  None) ,\
        ]

    def set_tags(node):
        node.tags = set()
        for child in node.children:
            node.tags = node.tags.union(child.tags)
        if node.label == "UNIT":
            node.tags.add(QuantityTags.U)
        elif node.label == "NUMBER":
            node.tags.add(QuantityTags.N)
        elif node.label == "NON-UNIT":
            node.tags.add(QuantityTags.V)
        elif node.label == "POWER" and QuantityTags.U in node.children[0].tags and node.children[1].tags == {QuantityTags.N}:
            node = tag_removal(node,QuantityTags.N)
        elif node.label == "SOLIDUS" and node.children[0].content == "1" and node.children[1].tags == {QuantityTags.U}:
            node = tag_removal(node,QuantityTags.N)
        elif node.label in ["PRODUCT","SOLIDUS","POWER"]:
            node = tag_removal(node,QuantityTags.U,lambda x: QuantityTags.N in x)
            node = tag(node,QuantityTags.V,lambda x: QuantityTags.N in x)
        elif node.label == "SPACE" and QuantityTags.V in node.children[1].tags:
            node = tag_removal(node,QuantityTags.U)
        return node

    productions = [( start_symbol, "Q" , relabel )]
    productions += [( "Q", "U" , create_node )]
    productions += [( "Q", "N" , create_node )]
    productions += [( "Q", "V" , create_node )]
    productions += [( "Q", "Q"+x+"Q", infix ) for x in list(" */^")]
    productions += [( "Q", "QQ" , append )]
    productions += [( "Q", "(Q)" , group )]

    def error_action_null(p,s,a,i,t,o):
        raise Exception("Parser reached impossible state, no 'NULL' token should exists in token list.")

    def error_action_start(p,s,a,i,t,o):
        raise Exception("Parser reached impossible state, 'START' should only be found once in token list.")

    def error_condition_incomplete_expression(items_token,next_symbol):
        if next_symbol.label == "END":
            return True
        else:
            return False

    def error_action_incomplete_expression(p,s,a,i,t,o):
        raise Exception("Input ended before expression was completed.")

    def error_condition_infix_missing_argument(items_token,next_symbol):
        if next_symbol.label in ["PRODUCT","SOLIDUS","POWER"]:
            return True
        else:
            return False

    def error_action_infix_missing_argument(p,s,a,i,t,o):
        raise Exception("Infix operator requires an argument on either side.")

    error_handler = [
        (lambda items_token,next_symbol: next_symbol.label == "NULL", error_action_null),
        (lambda items_token,next_symbol: next_symbol.label == "START", error_action_start),
        (error_condition_incomplete_expression, error_action_incomplete_expression),
        (error_condition_infix_missing_argument, error_action_infix_missing_argument),
    ]

    parser = SLR_Parser(token_list,productions,start_symbol,end_symbol,null_symbol,tag_handler=set_tags,error_handler=error_handler)
    tokens = parser.scan(expr)

    #print(tokens)
    #for k in range(0,17):
    #    print(str(k)+": "+str(parser._states_index[k])+"\n")
    #print(parser.parsing_table_to_string())
    quantity = parser.parse(tokens,verbose=False)

    if len(quantity) > 1:
        print(quantity)
        raise Exception("Parsed quantity does not have a single root.")

    quantity = PhysicalQuantity(quantity[0],messages=[],tag_handler=set_tags)

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
        #"q",
        #"10",
        #"-10.5*4",
        #"pi*5",
        #"5*pi",
        #"sin(-10.5*4)",
        #"kilogram/(metre second^2)",
        #"10 kilogram/(metre second^2)",
        #"10 kilogram*metre/second**2",
        #"-10.5 kg m/s^2",
        #"1 kg m/s^2 + 2 kg m/s^2",
        #"10 kilogram*metre*second**(-2)",
        #"10*pi kilogram*metre/second^2",
        #"(5.27*pi/sqrt(11) + 5*7)^(4.3)",
        #"(kilogram megametre^2)/(fs^4 daA)",
        #"(5.27*pi/sqrt(11) + 5*7)^(4.3) (kilogram megametre^2)/(fs^4 daA)",
        #"(5.27*pi/sqrt(11) + 5*7)^(2+2.3) (kilogram megametre^2)/(fs^4 daA)",
        #"(5*27/11 + 5*7)^(2*3) (kilogram megametre^2)/(fs^4 daA)",
        #"(pi+10) kg*m/s^2",
        #"10 kilogram*metre/second^2",
        "10 kg*m/s^2",
        #" 10 kg m/s^2 ",
        #"10 gram/metresecond",
        #"10 s/g + 5 gram*second^2 + 7 ms + 5 gram/second^3",
        #"10 second/gram * 7 ms * 5 gram/second",
        #"pi+metre second+pi",
        #"1/s^2",
        #"5/s^2",
        #"10 1/s^2",
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
        #messages = [x[1] for x in quantity.messages]
        #for criteria_tag in quantity.passed_dict:
        #    messages += [criteria.feedbacks[criteria_tag](criteria.results[criteria_tag](quantity))]
        #print("\n".join(messages))
        print(quantity.ast_root.tree_string())
    print("** COMPLETE **")