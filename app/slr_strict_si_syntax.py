# -------
# GLOBALS
# -------
#add_criterion("FULL_QUANTITY",\
#    lambda x: x.value != None and x.unit != None,\
#    lambda x: (x.value,x.unit),\
#    "")
#add_criterion("HAS_UNIT",\
#    lambda x: x.unit != None,\
#    lambda x: x.unit,\
#    "Quantity has unit(s).")
#add_criterion("ONLY_UNIT",
#    lambda x: x.value == None and x.unit != None,\
#    lambda x: x.unit,\
#    "Quantity only has unit(s).")
#add_criterion("NO_UNIT",
#    lambda x: x.unit == None,\
#    lambda x: None,\
#    "Quantity has no unit(s).")
#add_criterion("HAS_VALUE",\
#    lambda x: x.value != None,\
#    lambda x: x.value,\
#    "Quantity has value.")
#add_criterion("NO_VALUE",\
#    lambda tokens: "NON_UNIT" not in types(tokens) and "NUMBER" not in types(tokens),\
#    lambda tokens: None,\
#    "Quantity has value.")
#add_criterion("NUMBER_VALUE",\
#    lambda tokens: types(tokens) == ["NUMBER","SPACE","UNIT_EXPR"] or types(tokens) == ["NUMBER"],\
#    lambda tokens: tokens[0].content,\
#    "Value is a number.")
#add_criterion("EXPR_VALUE",\
#    lambda tokens: types(tokens) == ["NON_UNIT","SPACE","UNIT_EXPR"] or types(tokens) == ["NON_UNIT"],\
#    lambda tokens: tokens[0].content,\
#    "Value is an expression.")

# -------
# CLASSES
# -------

from enum import Enum
QuantityTags = Enum("QuantityTags",{v:i for i,v in enumerate("UVN",1)})

class PhysicalQuantity:

    def __init__(self,ast_root,messages):
        self.messages = messages
        self.ast_root = ast_root
        self.value = None
        self.unit = None
        self._rotate_until_root_is_split()
        if self.ast_root.label == "SPACE":
            self.value = self.ast_root.children[0]
            self.unit = self.ast_root.children[1]
        elif QuantityTags.U in self.ast_root.tags:
            self.unit = self.ast_root
        else:
            self.value = self.ast_root
        return

    def _rotate_right(self):
        if len(self.ast_root.children) > 0:
            old_root = self.ast_root
            new_root = old_root.children[0]
            if len(new_root.children) > 0:
                switch = new_root.children[-1]
                old_root.children[0] = switch
                new_root.children[-1] = old_root
            else:
                old_root.children = old_root.children[1:]
                new_root.children.append(old_root)
            for child in old_root.children:
                old_root.tags = old_root.tags | child.tags
                if QuantityTags.V in old_root.tags and QuantityTags.U in old_root.tags:
                    old_root.tags.remove(QuantityTags.U)
            for child in old_root.children:
                new_root.tags = new_root.tags | child.tags
                if QuantityTags.V in new_root.tags and QuantityTags.U in new_root.tags:
                    new_root.tags.remove(QuantityTags.U)
            self.ast_root = new_root
        else:
            raise Exception("Cannot rotate right.")
        return

    def _rotate_left(self):
        if len(self.ast_root.children) > 0:
            old_root = self.ast_root
            new_root = old_root.children[-1]
            if len(new_root.children) > 0:
                switch = new_root.children[0]
                old_root.children[-1] = switch
                new_root.children[0] = old_root
            else:
                old_root.children = old_root.children[0:-1]
                new_root.children.append(old_root)
            for child in old_root.children:
                old_root.tags = old_root.tags | child.tags
                if QuantityTags.V in old_root.tags and QuantityTags.U in old_root.tags:
                    old_root.tags.remove(QuantityTags.U)
            for child in old_root.children:
                new_root.tags = new_root.tags | child.tags
                if QuantityTags.V in new_root.tags and QuantityTags.U in new_root.tags:
                    new_root.tags.remove(QuantityTags.U)
            self.ast_root = new_root
        else:
            raise Exception("Cannot rotate left.")
        return

    def _rotate_until_root_is_split(self):
        if self.ast_root.label == "SPACE":
            if QuantityTags.V in self.ast_root.children[1].tags:
                self._rotate_left()
                self._rotate_until_root_is_split()
            elif QuantityTags.U in self.ast_root.children[0].tags:
                self._rotate_right()
                self._rotate_until_root_is_split()
        return

    # TODO: fix this function!
    def _find_value_unit_split(self,root=None):
        if root == None:
            root = self.ast_root
        split = None
        if root.label == "SPACE":
            if "U" not in root.children[0].tags and "U" in root.children[1].tags:
                split = root
            elif "U" in root.children[0].tags and "U" in root.children[1].tags:
                split = self._find_value_unit_split(root=root.children[0])
            else:
                split = self._find_value_unit_split(root=root.children[1])
        elif len(root.children) == 2:
            if "U" not in root.children[1].tags:
                split = self._find_value_unit_split(root=root.children[1])
            elif "U" in root.children[0].tags:
                split = self._find_value_unit_split(root=root.children[0])
        elif len(root.children) == 1:
            split = self._find_value_unit_split(root=root.children[0])
        elif len(root.children) == 0:
            split = root
        else:
            raise Exception("Node has too many children:\n"+self.tree_string(root))
        return split

# ---------
# FUNCTIONS
# ---------

from slr_parsing_utilities import SLR_Parser, relabel, join, catch_undefined, infix, group, tag, tag_transfer, tag_removal, node, append
from static_unit_conversion_arrays import list_of_SI_base_unit_dimensions, list_of_SI_prefixes

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
        ("E",          "UNIT_EXPR",      None) ,\
        ("Q",          "QUANTITY_NODE",  None) ,\
        ]

    def transfer_tags_op(op):
        def apply(p,o):
            return tag_removal(p,tag_transfer(p,op(p,o)),QuantityTags.U,lambda x: QuantityTags.V in x)
        return apply

    def tag_node(tag_value):
        def apply(p,o):
            return tag(p,node(p,o),tag_value)
        return apply

    productions = [( start_symbol, "Q" , relabel )]
    productions += [( "Q", "(Q)" , transfer_tags_op(group) )]
    productions += [( "Q", "QQ" , transfer_tags_op(append) )]
    productions += [( "Q", "U" , tag_node(QuantityTags.U) )]
    productions += [( "Q", "N" , tag_node(QuantityTags.N) )]
    productions += [( "Q", "V" , tag_node(QuantityTags.V) )]
    productions += [( "Q", "Q"+x+"Q", transfer_tags_op(infix) ) for x in list(" */^")]

    prods = []
    for prod in [(x[0],x[1]) for x in productions]:
        if prod in prods:
            print(f"duplicate: {prod}")
        prods.append(prod)

    parser = SLR_Parser(token_list,productions,start_symbol,end_symbol,null_symbol)
    tokens = parser.scan(expr)

    rules = [( "N", "N"+x+"N", join ) for x in list("*/^")]
    rules += [( "V", "N V", join ), ( "V", "V N", join )]
    rules += [( x, " "+x, join ) for x in list(" */^")]
    rules += [( x, x+" ", join ) for x in list(" */^")]
    tokens = parser.process(tokens,rules)

    #print(tokens)
    #print(parser.parsing_table_to_string())
    quantity = parser.parse(tokens,verbose=False,restart_on_error=False)

    if len(quantity) > 1:
        print(quantity)
        raise Exception("Parsed quantity does not have a single root.")

    print(str(quantity[0].tags)+" "+str(len(quantity[0].children)))

    quantity = PhysicalQuantity(quantity[0],[])

    return quantity

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
        "10 kilogram metre/second^2",
        "10 kg*m/s^2",
        " 10 kg m/s^2 ",
        "10 gram/metresecond",
        "10 second/gram + 5 gram*second^2 + 7 ms + 5 gram/second^3",
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
        quantity = SLR_strict_SI_parsing(expr)
        value = quantity.value.original_string() if quantity.value != None else None
        unit = quantity.unit.original_string() if quantity.unit != None else None

        print("Value: "+str(value))
        print("Unit: "+str(unit))
        #print(quantity.ast_root.tree_string())
    print("** COMPLETE **")