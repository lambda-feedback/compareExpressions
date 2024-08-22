# -------
# IMPORTS
# -------

import re
from enum import Enum
from .criteria_utilities import Criterion
from .expression_utilities import parse_expression, compute_relative_tolerance_from_significant_decimals, create_sympy_parsing_params
from .symbolic_comparison_evaluation import evaluation_function as symbolic_comparison
from .symbolic_comparison_preview import preview_function as symbolic_preview
from .feedback.quantity_comparison import criteria as physical_quantities_criteria
from .feedback.quantity_comparison import internal as physical_quantities_messages
from .feedback.quantity_comparison import answer_matches_response_graph
from .expression_utilities import substitute
from .slr_parsing_utilities import SLR_Parser, relabel, catch_undefined, infix, insert_infix, group, tag_removal, create_node, ExprNode, operate
from sympy import Basic, posify
from .unit_system_conversions import\
    set_of_SI_prefixes, set_of_SI_base_unit_dimensions, set_of_derived_SI_units_in_SI_base_units,\
    set_of_common_units_in_SI, set_of_very_common_units_in_SI, set_of_imperial_units, conversion_to_base_si_units

from .criteria_utilities import traverse

# -----------------
# QUANTITY HANDLING
# -----------------

QuantityTags = Enum("QuantityTags", {v: i for i, v in enumerate("UVNR", 1)})

class PhysicalQuantity:

    def __init__(self, name, parameters, ast_root, parser, messages=None, tag_handler=lambda x: x):
        self.name = name
        self.parameters = parameters
        prefixes = [x[0] for x in set_of_SI_prefixes]
        fundamental_units = [x[0] for x in set_of_SI_base_unit_dimensions]
        dimensions = [x[2] for x in set_of_SI_base_unit_dimensions]
        unsplittable_symbols = prefixes+fundamental_units+dimensions
        symbol_assumptions = tuple([(f'{s}','positive') for s in fundamental_units+dimensions])
        self.parsing_params = create_sympy_parsing_params(
            parameters,
            unsplittable_symbols=unsplittable_symbols,
            symbol_assumptions=symbol_assumptions,
        )
        if messages == None:
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
                    self.messages += [("REVERTED_UNIT", physical_quantities_messages["REVERTED_UNIT"](node.original[:node.start], node.content_string(), node.original[node.end+1:]))]
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
                expanded_unit = parse_expression(expanded_unit.content_string(), parsing_params)
                converted_unit = expanded_unit
            except Exception as e:
                raise Exception("SymPy was unable to parse the "+self.name+" unit") from e
            base_unit_dimensions = [(base_unit[0], base_unit[2]) for base_unit in set_of_SI_base_unit_dimensions]
            if self.value is not None:
                substitution_dict = {symbol: 1 for symbol in converted_unit.free_symbols if str(symbol) in [x[0] for x in set_of_SI_base_unit_dimensions]}
                converted_unit_factor = converted_unit.subs(substitution_dict).simplify()
                converted_unit = (converted_unit/converted_unit_factor).simplify(rational=True)
                converted_value = "("+str(converted_value)+")*("+str(converted_unit_factor)+")"
            converted_unit_string = str(converted_unit)
            converted_dimension = substitute(converted_unit_string, base_unit_dimensions)
            converted_dimension = parse_expression(converted_dimension, parsing_params)
        return converted_value, converted_unit, expanded_unit, converted_dimension



def SLR_generate_unit_dictionaries(units_string, strictness):

    units_sets_dictionary = {
        "SI": set_of_SI_base_unit_dimensions | set_of_derived_SI_units_in_SI_base_units,
        "common": set_of_SI_base_unit_dimensions | set_of_derived_SI_units_in_SI_base_units | set_of_common_units_in_SI | set_of_very_common_units_in_SI,
        "imperial": set_of_imperial_units,
    }

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
            tags = tags # Do not change tags
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
#                        elem.tags.remove(QuantityTags.U)
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


def quantity_comparison(response, answer, parameters, eval_response):

    eval_response.is_correct = False

    quantity_parser = SLR_quantity_parser(parameters)
    quantity_parsing = SLR_quantity_parsing

    # -----------------
    # CRITERIA HANDLING
    # -----------------

    quantities = dict()
    evaluated_criteria = dict()
    criteria = physical_quantities_criteria
    parameters = dict(parameters)
    input_criteria_string = parameters.pop("criteria", "")
    input_criteria = {"INPUT_CRITERIA_"+str(k): Criterion(crit) for (k, crit) in enumerate(input_criteria_string.split("."))}
    criteria.update(input_criteria)
    prefixes = [x[0] for x in set_of_SI_prefixes]
    fundamental_units = [x[0] for x in set_of_SI_base_unit_dimensions]
    dimensions = [x[2] for x in set_of_SI_base_unit_dimensions]
    unsplittable_symbols = prefixes+fundamental_units+dimensions
    symbol_assumptions = tuple([(f'{s}','positive') for s in fundamental_units+dimensions])
    parsing_params = create_sympy_parsing_params(parameters, unsplittable_symbols=unsplittable_symbols, symbol_assumptions=symbol_assumptions)

    def check_criterion(tag, arg_names=None):
        if arg_names is None:
            collect_args = True
            args = []
        else:
            collect_args = False
            args = tuple(quantities[name] for name in arg_names)
        if (tag, arg_names) in evaluated_criteria.keys():
            result = evaluated_criteria[(tag, arg_names)][0]
        else:
            criterion = criteria[tag]
            if criterion.check == None:
                result = True
            else:
                criterion_tokens = criteria_parser.scan(criterion.check)
                number_of_args = 0
                for token in criterion_tokens:
                    if token.label == "QUANTITY":
                        if collect_args is True:
                            token.content = quantities[token.content.strip()]
                            args.append(token.content)
                        else:
                            token.content = args[number_of_args]
                            number_of_args += 1
                criterion_parsed = criteria_parser.parse(criterion_tokens)[0]
    
                def execute(node):
                    key = node.label.strip()
                    if key in criteria_operations.keys():
                        executed_children = [execute(c) for c in node.children]
                        return criteria_operations[key](executed_children)
                    elif key == "QUANTITY" or key == "INPUT":
                        return node.content
                    elif "INPUT" in [c.label for c in node.children]:
                        executed_children = [execute(c) for c in node.children]
                        expression = "".join([str(c) for c in executed_children])
                        expression = parse_expression(expression, parsing_params)
                        return expression
                    return None
            result = execute(criterion_parsed)
            feedback = criteria[tag][result](args)
            evaluated_criteria.update({(tag, arg_names): (result, feedback)})
        return result

    def matches(inputs):
        if isinstance(inputs[0], PhysicalQuantity) and isinstance(inputs[1], PhysicalQuantity):
            value0 = inputs[0].standard_value
            unit0 = inputs[0].standard_unit
            value1 = inputs[1].standard_value
            unit1 = inputs[1].standard_unit
            value_match = False
            unit_match = False
            if value0 is None and value1 is None:
                value_match = True
            elif value0 is not None and value1 is not None:
                value_match = symbolic_comparison(value0, value1, parameters)["is_correct"]
            if unit0 is None and unit0 is None:
                unit_match = True
            elif unit0 is not None and unit1 is not None:
                unit_match = bool((unit0 - unit1).simplify() == 0)
            return value_match and unit_match
        elif isinstance(inputs[0], Basic) and isinstance(inputs[1], Basic):
            if inputs[0] is not None and inputs[1] is not None:
                dimension_match = bool((inputs[0] - inputs[1]).cancel().simplify().simplify() == 0) # TODO: Make separate function for checking equality of expressions that can be parsed
            else:
                dimension_match = False
            return dimension_match
        return False

    def compare(comparison):
        comparison_dict = {
            "=": lambda inputs: bool((inputs[0] - inputs[1]).cancel().simplify().simplify() == 0),
            "<=": lambda inputs: bool((inputs[0] - inputs[1]).cancel().simplify().simplify() <= 0),
            ">=": lambda inputs: bool((inputs[0] - inputs[1]).cancel().simplify().simplify() >= 0),
            "<": lambda inputs: bool((inputs[0] - inputs[1]).cancel().simplify().simplify() < 0),
            ">": lambda inputs: bool((inputs[0] - inputs[1]).cancel().simplify().simplify() > 0),
        }
        def wrap(inputs):
            if inputs[0] is not None and inputs[1] is not None:
                return comparison_dict[comparison](inputs)
            else:
                return False
        return wrap

    criteria_operations = {
        "and":           lambda x: x[0] and x[1],
        "not":           lambda x: not x[0],
        "has":           lambda x: x[0] is not None,
        "unit":          lambda quantity: quantity[0].unit,
        "expanded_unit": lambda quantity: quantity[0].expanded_unit,
        "base_unit":     lambda quantity: quantity[0].standard_unit,
        "value":         lambda quantity: quantity[0].value,
        "is_number":     lambda value: value[0] is not None and value[0].tags == {QuantityTags.N},
        "is_expression": lambda value: value[0] is not None and QuantityTags.V in value[0].tags,
        "matches":       matches,
        "dimension":     lambda quantity: quantity[0].dimension,
        "=":             compare("="),
        "<=":            compare("<="),
        ">=":            compare(">="),
        "<":             compare("<"),
        ">":             compare(">"),
    }

    def generate_criteria_parser():
        start_symbol = "START"
        end_symbol = "END"
        null_symbol = "NULL"

        token_list = [
            (start_symbol,   start_symbol),
            (end_symbol,     end_symbol),
            (null_symbol,    null_symbol),
            (" *BOOL *",     "BOOL"),
            (" *UNIT *",     "UNIT"),
            (" *VALUE *",    "VALUE"),
            (" *QUANTITY *", "QUANTITY"),
            (" *DIMENSION *", "DIMENSION"),
            ("\( *",         "START_DELIMITER"),
            (" *\)",         "END_DELIMITER"),
            ("response",     "QUANTITY"),
            ("answer",       "QUANTITY"),
            ("INPUT",        "INPUT", catch_undefined),
        ]
        token_list += [(" *"+x+" *", " "+x+" ") for x in criteria_operations.keys()]

        productions = [
            ("START",     "BOOL", create_node),
            ("BOOL",      "BOOL and BOOL", infix),
            ("BOOL",      "UNIT matches UNIT", infix),
            ("BOOL",      "VALUE matches VALUE", infix),
            ("BOOL",      "QUANTITY matches QUANTITY", infix),
            ("BOOL",      "DIMENSION matches DIMENSION", infix),
            ("BOOL",      "not(BOOL)", operate(1)),
            ("BOOL",      "has(UNIT)", operate(1)),
            ("BOOL",      "has(VALUE)", operate(1)),
            ("BOOL",      "is_number(VALUE)", operate(1)),
            ("BOOL",      "is_expression(VALUE)", operate(1)),
            ("BOOL",      "UNIT=UNIT", infix),
            ("BOOL",      "UNIT<=UNIT", infix),
            ("BOOL",      "UNIT>=UNIT", infix),
            ("BOOL",      "UNIT<UNIT", infix),
            ("BOOL",      "UNIT>UNIT", infix),
            ("UNIT",      "unit(QUANTITY)", operate(1)),
            ("UNIT",      "base_unit(QUANTITY)", operate(1)),
            ("UNIT",      "expanded_unit(QUANTITY)", operate(1)),
            ("UNIT",      "INPUT UNIT", group(2, empty=True)),
            ("UNIT",      "UNIT INPUT", group(2, empty=True)),
            ("VALUE",     "value(QUANTITY)", operate(1)),
            ("QUANTITY",  "INPUT", create_node),
            ("DIMENSION", "dimension(QUANTITY)", operate(1)),
        ]

        return SLR_Parser(token_list, productions, start_symbol, end_symbol, null_symbol)

    criteria_parser = generate_criteria_parser()

    # -------------------
    # QUANTITY COMPARISON
    # -------------------

    for criterion in criteria.values():
        if criterion.check is None:
            continue
        criterion_tokens = criteria_parser.scan(criterion.check)
        relevant_quantities = set()
        relevant_criteria_operations = set()
        for token in criterion_tokens:
            if token.label == "QUANTITY":
                content = token.content.strip()
                if content != "QUANTITY":
                    relevant_quantities.add(token.content.strip())
                    if content not in quantities.keys():
                        if content == "answer":
                            try:
                                ans_parsed = quantity_parsing(answer, parameters, quantity_parser, "answer")
                            except Exception as e:
                                raise Exception("Could not parse quantity expression in answer: "+str(e)) from e
                            quantities.update({"answer": ans_parsed})
                        elif content == "response":
                            try:
                                res_parsed = quantity_parsing(response, parameters, quantity_parser, "response")
                            except Exception as e:
                                eval_response.add_feedback(("PARSE_EXCEPTION", str(e)))
                                eval_response.is_correct = False
                                return eval_response
                            quantities.update({"response": res_parsed})
                        else:
                            relevant_quantities.update({token.content.strip(): token.content.strip()})
            elif token.label.strip() in criteria_operations.keys():
                relevant_criteria_operations.add(token.label.strip())

    # Collects messages from parsing the response, these needs to be returned as feedback later
    if "response" in quantities.keys():
        for message in quantities["response"].messages:
            eval_response.add_feedback(message)

    # Computes the desired tolerance used for numerical computations based on the formatting of the answer
    if check_criterion("NUMBER_VALUE", ("answer",)):
        parameters["rtol"] = parameters.get(
            "rtol",
            compute_relative_tolerance_from_significant_decimals(
                quantities["answer"].value.content_string()
            ),
        )

    eval_response.latex = quantities["response"].latex_string

    check = lambda label, criterion: check_criterion(label, arg_names=("response", "answer"))

    #is_correct = answer_matches_response_graph.traverse(check)
    is_correct = traverse(answer_matches_response_graph,check)
    eval_response.is_correct = is_correct

    for (tag, result) in evaluated_criteria.items():
        if len(result[1].strip()) > 0:
            eval_response.add_feedback((tag[0], "- "+result[1]+"<br>"))

    return eval_response
