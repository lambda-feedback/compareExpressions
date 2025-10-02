import re
from enum import Enum
from .expression_utilities import (
    substitute,
    create_sympy_parsing_params,
    parse_expression
)
from .slr_parsing_utilities import (
    SLR_Parser,
    relabel,
    catch_undefined,
    infix,
    insert_infix,
    group,
    tag_removal,
    create_node,
    ExprNode
)
from .unit_system_conversions import\
    set_of_SI_prefixes, set_of_SI_base_unit_dimensions, set_of_derived_SI_units_in_SI_base_units,\
    set_of_common_units_in_SI, set_of_very_common_units_in_SI, set_of_imperial_units, conversion_to_base_si_units
from ..feedback.physical_quantity import feedback_string_generators as physical_quantity_feedback_string_generators

from ..preview_implementations.symbolic_preview import preview_function as symbolic_preview

QuantityTags = Enum("QuantityTags", {v: i for i, v in enumerate("UVNR", 1)})

units_sets_dictionary = {
    "SI": set_of_SI_base_unit_dimensions | set_of_derived_SI_units_in_SI_base_units,
    "common": set_of_SI_base_unit_dimensions | set_of_derived_SI_units_in_SI_base_units | set_of_common_units_in_SI | set_of_very_common_units_in_SI,
    "imperial": set_of_imperial_units,
}


class PhysicalQuantity:

    def __init__(self, name, parameters, ast_root, parser, messages=None, tag_handler=lambda x: x):
        self.name = name
        self.parameters = parameters
        prefixes = set(x[0] for x in set_of_SI_prefixes)
        fundamental_units = set(x[0] for x in set_of_SI_base_unit_dimensions)
        units_string = parameters.get("units_string", "SI common imperial")
        valid_units = set()
        for key in units_sets_dictionary.keys():
            if key in units_string:
                for unit in units_sets_dictionary[key]:
                    valid_units = valid_units.union(set((unit[0],)))
        dimensions = set(x[2] for x in set_of_SI_base_unit_dimensions)
        unsplittable_symbols = list(prefixes | fundamental_units | valid_units | dimensions)
        symbol_assumptions = tuple((f'{s}', 'positive') for s in unsplittable_symbols)
        self.parsing_params = create_sympy_parsing_params(
            parameters,
            unsplittable_symbols=unsplittable_symbols,
            symbol_assumptions=symbol_assumptions,
        )
        if messages is None:
            self.messages = []
        else:
            self.messages = messages
        self.ast_root = ast_root
        self.parser = parser
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
        if self.value is not None:
            def revert_content(node):
                if node.label != "GROUP":
                    node.content = node.original[node.start:node.end+1]
                if node.label == "UNIT" or QuantityTags.U in node.tags:
                    self.messages += [
                        (
                            name+"_REVERTED_UNIT_"+str(len(self.messages)),
                            physical_quantity_feedback_string_generators["INTERNAL"]("REVERTED_UNIT")(
                                {
                                    'before': node.original[:node.start],
                                    'marked': node.content_string(),
                                    'after': node.original[node.end+1:]
                                }
                            )
                        )
                    ]
                return ["", ""]
            self.value.traverse(revert_content)
        self.value_latex_string = self._value_latex(parameters)
        self.unit_latex_string = None
        if self.unit is not None:
            self.unit_latex_string = "".join(self._unit_latex(self.unit))
        separator = ""
        if self.value_latex_string is not None and self.unit_latex_string is not None:
            separator = "~"
        value_latex = self.value_latex_string if self.value_latex_string is not None else ""
        unit_latex = self.unit_latex_string if self.unit_latex_string is not None else ""
        self.latex_string = value_latex+separator+unit_latex
        self.standard_value, self.standard_unit, self.expanded_unit, self.dimension = self._all_forms()
        return

    def _rotate(self, direction):
        # right: direction = 1
        # left: direction = 0
        if direction not in {0, 1}:
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
        old_root.tags = self.tag_handler(old_root)
        new_root.tags = self.tag_handler(new_root)
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

    def _value_latex(self, parameters):
        if self.value is not None:
            preview_parameters = {**parameters}
            prefixes = set(x[0] for x in set_of_SI_prefixes)
            fundamental_units = set(x[0] for x in set_of_SI_base_unit_dimensions)
            units_string = parameters.get("units_string", "SI common imperial")
            valid_units = set()
            for key in units_sets_dictionary.keys():
                if key in units_string:
                    for unit in units_sets_dictionary[key]:
                        valid_units = valid_units.union(set((unit[0], unit[1])+unit[3]+unit[4]))
            dimensions = set(x[2] for x in set_of_SI_base_unit_dimensions)
            unsplittable_symbols = list(prefixes | fundamental_units | valid_units | dimensions)
            preview_parameters.update({"reserved_keywords": preview_parameters.get("reserved_keywords", [])+unsplittable_symbols})
            if "rtol" not in preview_parameters.keys():
                preview_parameters.update({"rtol": 1e-12})
            original_string = self.value.original_string()
            value = symbolic_preview(original_string, preview_parameters)
            value_latex = value["preview"]["latex"]
            return value_latex
        return None

    def _unit_latex(self, node):
        # TODO: skip unnecessary parenthesis (i.e. check for GROUP children for powers and fraction and inside groups)
        content = node.content
        children = node.children
        if node.label == "PRODUCT":
            return self._unit_latex(children[0])+["\\cdot"]+self._unit_latex(children[1])
        elif node.label == "NUMBER":
            return [content]
        elif node.label == "SPACE":
            return self._unit_latex(children[0])+["~"]+self._unit_latex(children[1])
        elif node.label == "UNIT":
            return ["\\mathrm{"]+[content]+["}"]
        elif node.label == "GROUP":
            out = [content[0]]
            for child in children:
                out += self._unit_latex(child)
            return out+[content[1]]
        elif node.label == "POWER":
            return self._unit_latex(children[0])+["^{"]+self._unit_latex(children[1])+["}"]
        elif node.label == "SOLIDUS":
            return ["\\frac{"]+self._unit_latex(children[0])+["}{"]+self._unit_latex(children[1])+["}"]
        else:
            return [content]

    def _expand_units(self, node):
        if node.label == "UNIT" and len(node.children) == 0 and node.content not in [x[0] for x in set_of_SI_base_unit_dimensions]:
            expanded_unit_content = conversion_to_base_si_units[node.content]
            node = self.parser.parse(self.parser.scan(expanded_unit_content))[0]
        for k, child in enumerate(node.children):
            node.children[k] = self._expand_units(child)
        return node

    def _all_forms(self):
        parsing_params = self.parsing_params
        converted_value = self.value.content_string() if self.value is not None else None
        converted_unit = None
        expanded_unit = None
        converted_dimension = parse_expression("1", parsing_params)
        if self.unit is not None:
            converted_unit = self.unit.copy()
            expanded_unit = self._expand_units(converted_unit)
            converted_unit_string = expanded_unit.content_string()
            try:
                expanded_unit = parse_expression(converted_unit_string, parsing_params)
                converted_unit = expanded_unit
            except Exception as e:
                raise Exception("SymPy was unable to parse the "+self.name+" unit") from e
            base_unit_dimensions = [(base_unit[0], base_unit[2]) for base_unit in set_of_SI_base_unit_dimensions]
            if self.value is not None:
                substitution_dict = {symbol: 1 for symbol in converted_unit.free_symbols if str(symbol) in [x[0] for x in set_of_SI_base_unit_dimensions]}
                converted_unit_factor = converted_unit.subs(substitution_dict).simplify()
                converted_unit = (converted_unit/converted_unit_factor).simplify(rational=True)
                converted_value = "("+str(converted_value)+")*("+str(converted_unit_factor)+")"
            converted_dimension = substitute(converted_unit_string, base_unit_dimensions)
            converted_dimension = parse_expression(converted_dimension, parsing_params)
        if converted_value is not None:
            converted_value = parse_expression(converted_value, parsing_params)
        return converted_value, converted_unit, expanded_unit, converted_dimension


def SLR_generate_unit_dictionaries(units_string, strictness):

    if strictness == "legacy":
        strictness = "natural"

    units_tuples = set()
    for key in units_sets_dictionary.keys():
        if key in units_string:
            units_tuples |= units_sets_dictionary[key]

    units_end = dict()
    if strictness == "strict":
        units = {x[0]: x[0] for x in units_tuples}
        units_short_to_long = {x[1]: x[0] for x in units_tuples}
        units_long_to_short = {x[0]: x[1] for x in units_tuples}
    elif strictness == "natural":
        units = {x[0]: x[0] for x in units_tuples}
        for unit in units_tuples:
            units.update({x: unit[0] for x in unit[3]})
            units_end.update({x: unit[0] for x in unit[4]})
        units_short_to_long = {x[1]: x[0] for x in units_tuples}
        units_long_to_short = {x[0]: x[1] for x in units_tuples}
        for unit in units_tuples:
            units_long_to_short.update({x: unit[1] for x in unit[3]})
            units_long_to_short.update({x: unit[1] for x in unit[4]})

    prefixes = {x[0]: x[0] for x in set_of_SI_prefixes}
    prefixes_long_to_short = {x[0]: x[1] for x in set_of_SI_prefixes}
    prefixed_units = {**units}
    for unit in units.keys():
        for prefix in prefixes.keys():
            prefixed_units.update({prefix+unit: prefix+units[unit]})
            # If prefixed short form overlaps with short form for other unit, do not include prefixed form
            if prefixes_long_to_short[prefix]+units_long_to_short[unit] not in units_short_to_long.keys():
                prefixed_units.update(
                    {
                        prefixes_long_to_short[prefix]+units_long_to_short[unit]: prefix+units[unit]
                    }
                )

    prefixed_units_end = {**units_end}
    for unit in units_end.keys():
        for prefix in prefixes.keys():
            prefixed_units_end.update(
                {
                    prefix+unit: prefix+units_end[unit],
                }
            )

    return {**units, **units_short_to_long}, prefixed_units, units_end, prefixed_units_end


def set_tags(strictness):
    def tag_handler(node):
        tags = set()
        for child in node.children:
            tags = tags.union(child.tags)
        if node.label == "UNIT":
            tags.add(QuantityTags.U)
        elif node.label == "NUMBER":
            tags.add(QuantityTags.N)
        elif node.label == "NON-UNIT":
            tags.add(QuantityTags.V)
        elif node.label == "POWER" and QuantityTags.U in node.children[0].tags and node.children[1].tags == {QuantityTags.N}:
            tags.remove(QuantityTags.N)
        elif node.label == "SOLIDUS" and node.children[0].content == "1" and node.children[1].tags == {QuantityTags.U}:
            tags.remove(QuantityTags.N)
        elif node.label == "SOLIDUS" and node.children[0].tags == {QuantityTags.N} and node.children[1].tags == {QuantityTags.N}:
            tags = tags  # Do not change tags
        elif node.label in ["PRODUCT", "SOLIDUS", "POWER"]:
            if any(x in tags for x in [QuantityTags.N, QuantityTags.V, QuantityTags.R]):
                if QuantityTags.U in tags:
                    tags.remove(QuantityTags.U)
                if QuantityTags.N in tags:
                    tags.add(QuantityTags.V)
        elif node.label in "SPACE" and QuantityTags.V in node.children[1].tags:
            if QuantityTags.U in tags:
                tags.remove(QuantityTags.U)
        elif node.label == "GROUP" and len(node.content[0]+node.content[1]) == 0:
            if strictness == "strict":
                for (k, child) in enumerate(node.children):
                    node.children[k] = tag_removal(child, QuantityTags.U)
                if QuantityTags.U in tags:
                    tags.remove(QuantityTags.U)
                    tags.add(QuantityTags.R)
            elif strictness == "natural":
                for child in node.children:
                    if QuantityTags.V in child.tags and QuantityTags.U in tags:
                        tags.remove(QuantityTags.U)
                        break
        return tags
    return tag_handler


def SLR_quantity_parser(parameters):
    units_string = parameters.get("units_string", "SI common imperial")
    strictness = parameters.get("strictness", "natural")
    if strictness == "legacy":
        strictness = "natural"
    units_dictionary, prefixed_units_dictionary, units_end_dictionary, prefixed_units_end_dictionary = \
        SLR_generate_unit_dictionaries(units_string, strictness)
    max_unit_name_length = max(len(x) for x in [units_dictionary.keys()]+[units_end_dictionary.keys()])

    if strictness == "strict":
        units_dictionary.update(prefixed_units_dictionary)

        def starts_with_unit(string):
            token = None
            unit = None
            for k in range(max_unit_name_length, -1, -1):
                unit = units_dictionary.get(string[0:k+1], None)
                if unit is not None:
                    token = string[0:k+1]
                    break
            return token, unit
    elif strictness == "natural":
        chars_in_keys = set()
        for key in {
            **units_dictionary,
            **prefixed_units_dictionary,
            **prefixed_units_end_dictionary,
            **units_end_dictionary
        }.keys():
            for c in key:
                chars_in_keys.add(c)

        def starts_with_unit(string):
            units_end = {**prefixed_units_end_dictionary, **units_end_dictionary}
            units = {**prefixed_units_dictionary, **units_dictionary}
            token = None
            unit = None
            end_point = len(string)
            for k, c in enumerate(string):
                if c not in chars_in_keys:
                    end_point = k
                    break
            if end_point > 0:
                local_string = string[0:end_point]
                # Check if string is end unit alternative
                unit = units_end.get(local_string, None)
                if unit is not None:
                    token = local_string
                else:
                    # Check if string starts with unit
                    for k in range(len(local_string), -1, -1):
                        unit = units.get(local_string[0:k], None)
                        if unit is not None:
                            token = local_string[0:k]
                            break
            return token, unit

    def starts_with_number(string):
        match_content = re.match('^-?(0|[1-9]\d*)?(\.\d+)?(?<=\d)(e-?(0|[1-9]\d*))?', string)
        match_content = match_content.group() if match_content is not None else None
        return match_content, match_content

    start_symbol = "START"
    end_symbol = "END"
    null_symbol = "NULL"

    token_list = [
        (start_symbol, start_symbol),
        (end_symbol,   end_symbol),
        (null_symbol,  null_symbol),
        (" +",         "SPACE"),
        (" *\* *",     "PRODUCT"),
        (" */ *",      "SOLIDUS"),
        (" *\^ *",     "POWER"),
        (" *\*\* *",   "POWER"),
        ("\( *",       "START_DELIMITER"),
        (" *\)",       "END_DELIMITER"),
        ("N",          "NUMBER",        starts_with_number),
        ("U",          "UNIT",          starts_with_unit),
        ("V",          "NON-UNIT",      catch_undefined),
        ("Q",          "QUANTITY_NODE", None),
    ]

    if strictness == "strict":
        juxtaposition = group(2, empty=True)
    elif strictness == "natural":
        def juxtaposition_natural(production, output, tag_handler):
            is_unit = [False, False]
            for k, elem in enumerate(output[-2:], -2):
                if isinstance(elem, ExprNode):
                    is_unit[k] = QuantityTags.U in elem.tags and elem.label != "GROUP"
                    is_unit[k] = is_unit[k] or (elem.tags == {QuantityTags.U} and elem.label == "GROUP")
                else:
                    is_unit[k] = elem.label == "UNIT"
            if all(is_unit):
                return insert_infix(" ", "SPACE")(production, output, tag_handler)
            else:
                for k, elem in enumerate(output[-2:], -2):
                    if is_unit[k] is True:
                        elem.tags.add(QuantityTags.V)
                return group(2, empty=True)(production, output, tag_handler)
        juxtaposition = juxtaposition_natural

    productions = [(start_symbol, "Q", relabel)]
    productions += [("Q", "Q"+x+"Q", infix) for x in list(" */")]
    productions += [("Q", "QQ", juxtaposition)]
    productions += [("Q", "Q^Q", infix)]
    productions += [("Q", "(Q)",  group(1))]
    productions += [("Q", "U", create_node)]
    productions += [("Q", "N", create_node)]
    productions += [("Q", "V", create_node)]

    def error_action_null(p, s, a, i, t, o):
        raise Exception("Parser reached impossible state, no 'NULL' token should exists in token list.")

    def error_action_start(p, s, a, i, t, o):
        raise Exception("Parser reached impossible state, 'START' should only be found once in token list.")

    def error_condition_incomplete_expression(items_token, next_symbol):
        if next_symbol.label == "END":
            return True
        else:
            return False

    def error_action_incomplete_expression(p, s, a, i, t, o):
        raise Exception("Input ended before expression was completed.")

    def error_condition_infix_missing_argument(items_token, next_symbol):
        if next_symbol.label in ["PRODUCT", "SOLIDUS", "POWER"]:
            return True
        else:
            return False

    def error_action_infix_missing_argument(p, s, a, i, t, o):
        raise Exception("Infix operator requires an argument on either side.")

    error_handler = [
        (lambda items_token, next_symbol: next_symbol.label == "NULL", error_action_null),
        (lambda items_token, next_symbol: next_symbol.label == "START", error_action_start),
        (error_condition_incomplete_expression, error_action_incomplete_expression),
        (error_condition_infix_missing_argument, error_action_infix_missing_argument),
    ]

    parser = SLR_Parser(token_list, productions, start_symbol, end_symbol, null_symbol, tag_handler=set_tags(strictness), error_handler=error_handler)
    return parser


def SLR_quantity_parsing(expr, parameters, parser, name):
    expr = expr.strip()
    tokens = parser.scan(expr)

    quantity = parser.parse(tokens, verbose=False)

    if len(quantity) > 1:
        raise Exception("Parsed quantity does not have a single root.")

    tag_handler = set_tags(parameters.get("strictness", "strict"))
    return PhysicalQuantity(name, parameters, quantity[0], parser, messages=[], tag_handler=tag_handler)
