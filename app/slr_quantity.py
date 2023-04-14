# -------
# IMPORTS
# -------

import re
from app.expression_utilities import parse_expression
from app.symbolic_equal import evaluation_function as symbolicEqual
from app.comparison_utilities import symbolic_comparison, compute_relative_tolerance_from_significant_decimals
from app.criteria_utilities import CriterionCollection
from app.feedback.physical_quantities import criteria as physical_quantities_criteria
from app.feedback.physical_quantities import internal as physical_quantities_messages
from app.feedback.physical_quantities import QuantityTags
#from app.physical_quantities_criteria_functions import check_criterion
from app.slr_parsing_utilities import SLR_Parser, relabel, catch_undefined, infix, insert_infix, group, tag_removal, create_node, ExprNode, operate
from app.unit_system_conversions import\
    set_of_SI_prefixes, set_of_SI_base_unit_dimensions, set_of_derived_SI_units_in_SI_base_units,\
    set_of_common_units_in_SI, set_of_very_common_units_in_SI, set_of_imperial_units, conversion_to_base_si_units


# -------
# CLASSES
# -------

criteria = CriterionCollection()

criteria.add_criterion(
        "FULL_QUANTITY",
        lambda x: x.value is not None and x.unit is not None,
        lambda x: (x.value.content_string(), x.unit.content_string()),
        lambda result: "Quantity has both value and unit.<br>Value: "+result[0]+"<br>Unit: "+result[1]
    )
criteria.add_criterion(
        "HAS_UNIT",
        lambda x: x.unit is not None,
        lambda x: x.unit.content_string(),
        lambda result: "Quantity has unit: "+result
    )
criteria.add_criterion(
        "ONLY_UNIT",
        lambda x: x.value is None and x.unit is not None,
        lambda x: x.unit.content_string(),
        lambda result: "Quantity has no value, only unit(s): "+result
    )
criteria.add_criterion(
        "NO_UNIT",
        lambda x: x.unit is None,
        lambda x: None,
        lambda result: "Quantity has no unit."
    )
criteria.add_criterion(
        "HAS_VALUE",
        lambda x: x.value is not None,
        lambda x: x.value.content_string(),
        lambda result: "Quantity has value: "+result
    )
criteria.add_criterion(
        "NO_VALUE",
        lambda x: x.value is None,
        lambda x: None,
        lambda result: "Quantity has no value."
    )
criteria.add_criterion(
        "NUMBER_VALUE",
        lambda x: x.value is not None and x.value.tags == {QuantityTags.N},
        lambda x: x.value.content_string(),
        lambda result: "Value is a number: "+result
    )
criteria.add_criterion(
        "EXPR_VALUE",
        lambda x: x.value is not None and QuantityTags.V in x.value.tags,
        lambda x: x.value.content_string(),
        lambda result: "Value is an expression: "+result
    )
criteria.add_criterion(
        "REVERTED_UNIT",
        lambda x: "REVERTED_UNIT" in [y[0] for y in x.messages],
        lambda x: "\n".join([y[1] for y in x.messages if y[0] == "REVERTED_UNIT"]),
        lambda result: "There were parsing ambiguities:\n"+result
    )

# -----------------
# QUANTITY HANDLING
# -----------------


class PhysicalQuantity:

    def __init__(self, ast_root, criteria, messages=[], tag_handler=lambda x: x):
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
        if self.value is not None:
            def revert_content(node):
                if node.label != "GROUP":
                    node.content = node.original[node.start:node.end+1]
                if node.label == "UNIT":
                    self.messages += [("REVERTED_UNIT", physical_quantities_messages["REVERTED_UNIT"](node.original[:node.start], node.content, node.original[node.end+1:]))]
                return ["", ""]
            self.value.traverse(revert_content)
        self.passed_dict = dict()
        for tag in criteria.tags:
            if criteria.checks[tag](self):
                self.passed_dict.update({tag: criteria.feedbacks[tag](criteria.results[tag](self))})
        return

    def passed(self, tag):
        return self.passed_dict.get(tag, None)

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


def SLR_quantity_parser(units_string="SI common imperial", strictness="natural"):
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
            units_end = prefixed_units_end_dictionary | units_end_dictionary
            units = prefixed_units_dictionary | units_dictionary
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
                    is_unit[k] = QuantityTags.U in elem.tags
                else:
                    is_unit[k] = elem.label == "UNIT"
            if all(is_unit):
                return insert_infix(" ", "SPACE")(production, output, tag_handler)
            else:
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


def SLR_quantity_parsing(expr, units_string="SI", strictness="strict"):

    parser = SLR_quantity_parser(units_string=units_string, strictness=strictness)

    expr = expr.strip()
    tokens = parser.scan(expr)

    quantity = parser.parse(tokens, verbose=False)

    if len(quantity) > 1:
        raise Exception("Parsed quantity does not have a single root.")

    tag_handler = set_tags(strictness)
    quantity = PhysicalQuantity(quantity[0], messages=[], criteria=criteria, tag_handler=tag_handler)

    def unit_latex(node):
        # TODO: skip unnecessary parenthesis (i.e. check for GROUP children for powers and fraction and inside groups)
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

    unit_latex_string = "".join(unit_latex(quantity.unit)) if quantity.unit is not None else None

    return quantity, unit_latex_string

# -----------------
# CRITERIA HANDLING
# -----------------

criteria_operations = {
    "and":           lambda x: x[0] and x[1],
    "not":           lambda x: not x[0],
    "has":           lambda x: x[0] is not None,
    "unit":          lambda quantity: quantity[0].unit,
    "value":         lambda quantity: quantity[0].value,
    "is_number":     lambda value: value[0] is not None and value[0].tags == {QuantityTags.N},
    "is_expression": lambda value: value[0] is not None and QuantityTags.V in value[0].tags,
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
        ("\( *",         "START_DELIMITER"),
        (" *\)",         "END_DELIMITER"),
        ("response",     "QUANTITY"),
        ("answer",       "QUANTITY"),
        ("INPUT",        "INPUT", catch_undefined),
    ]
    token_list += [(" *"+x+" *"," "+x+" ") for x in criteria_operations.keys()]

    productions = [
        ("START",    "BOOL", create_node),
        ("BOOL",     "BOOL and BOOL", infix),
        ("BOOL",     "UNIT matches UNIT", infix),
        ("BOOL",     "VALUE matches VALUE", infix),
        ("BOOL",     "QUANTITY matches QUANTITY", infix),
        ("BOOL",     "not(BOOL)", operate(1)),
        ("BOOL",     "has(UNIT)", operate(1)),
        ("BOOL",     "has(VALUE)", operate(1)),
        ("BOOL",     "is_number(VALUE)", operate(1)),
        ("BOOL",     "is_expression(VALUE)", operate(1)),
        ("UNIT",     "unit(QUANTITY)", operate(1)),
        ("VALUE",    "value(QUANTITY)", operate(1)),
        ("QUANTITY", "INPUT", create_node),
    ]

    return SLR_Parser(token_list, productions, start_symbol, end_symbol, null_symbol)

criteria_parser = generate_criteria_parser()

# -------------------
# QUANTITY COMPARISON
# -------------------

def quantity_comparison(response, answer, parameters, parsing_params, eval_response):
    # Removing SLR from function names since the implementation of the parser should not matter here
    quantity_parser = SLR_quantity_parser
    quantity_parsing = SLR_quantity_parsing
    # Routine for comparing quantities starts here
    eval_response.is_correct = True
    units_string = parameters.get("units_string", "SI")
    strictness = parameters.get("strictness", "strict")
    #try:
    ans_parsed, ans_latex = quantity_parsing(answer, units_string=units_string, strictness=strictness)
    #except Exception as e:
    #    raise Exception("Could not parse quantity expression in answer: "+str(e)) from e

    try:
        res_parsed, res_latex = quantity_parsing(response, units_string=units_string, strictness=strictness)
    except Exception as e:
        eval_response.add_feedback(("PARSE_EXCEPTION", str(e)))
        eval_response.is_correct = False
        return eval_response

    # Collects messages from parsing the response, these needs to be returned as feedback later
    for message in res_parsed.messages:
        eval_response.add_feedback(message)

    # Computes the desired tolerance used for numerical computations based on the formatting of the answer
    if ans_parsed.passed("NUMBER_VALUE"):
        parameters["rtol"] = parameters.get(
            "rtol",
            compute_relative_tolerance_from_significant_decimals(
                ans_parsed.value.content_string()
            ),
        )

    def expand_units(node):
        parser = quantity_parser(units_string, strictness)
        if node.label == "UNIT" and len(node.children) == 0 and node.content not in [x[0] for x in set_of_SI_base_unit_dimensions]:
            expanded_unit_content = conversion_to_base_si_units[node.content]
            node = parser.parse(parser.scan(expanded_unit_content))[0]
        for k, child in enumerate(node.children):
            node.children[k] = expand_units(child)
        return node

    def convert_to_standard_unit(q):
        q_converted_value = q.value.content_string() if q.value is not None else None
        q_converted_unit = None
        if q.unit is not None:
            q_converted_unit = q.unit.copy()
            q_converted_unit = expand_units(q_converted_unit)
            q_converted_unit = q_converted_unit.content_string()
            q_converted_unit = parse_expression(q_converted_unit, parsing_params)
        if q.passed("FULL_QUANTITY"):
            try:
                q_converted_unit_factor = q_converted_unit.subs({name: 1 for name in [x[0] for x in set_of_SI_base_unit_dimensions]}).simplify()
                q_converted_unit = (q_converted_unit/q_converted_unit_factor).simplify()
            except Exception as e:
                raise Exception("SymPy was unable to parse the answer unit") from e
            q_converted_value = "("+str(q_converted_value)+")*("+str(q_converted_unit_factor)+")"
        return q_converted_value, q_converted_unit

    ans_converted_value, ans_converted_unit = convert_to_standard_unit(ans_parsed)
    res_converted_value, res_converted_unit = convert_to_standard_unit(res_parsed)

    response_latex = []

    if res_parsed.passed("HAS_VALUE"):
        # TODO redesign symbolicEqual so that it can easily return latex version of input
        if ans_parsed.passed("NUMBER_VALUE") and not res_parsed.passed("NUMBER_VALUE"):
            preview_parameters = {**parameters}
            del preview_parameters["rtol"]
            value_comparison_response = symbolicEqual(res_parsed.value.original_string(), "0", preview_parameters)
        else:
            value_comparison_response = symbolicEqual(res_parsed.value.original_string(), "0", parameters)
        # TODO Update symbolicEqual to use new evaluationResponse system
        # response_latex += [value_comparison_response.response_latex]
        response_latex += [value_comparison_response.get("response_latex", "")]
    if res_latex is not None and len(res_latex) > 0:
        if len(response_latex) > 0:
            response_latex += ["~"]
        response_latex += [res_latex]
    eval_response.latex = "".join(response_latex)

    def compare_response_and_answer(comp_tag, action, not_res_tag, not_res_message, not_ans_tag, not_ans_message):
        if res_parsed.passed(comp_tag) and ans_parsed.passed(comp_tag):
            eval_response.is_correct = eval_response.is_correct and action()
        elif not res_parsed.passed(comp_tag) and ans_parsed.passed(comp_tag):
            eval_response.add_feedback((not_res_tag, not_res_message))
            eval_response.is_correct = False
        elif res_parsed.passed(comp_tag) and not ans_parsed.passed(comp_tag):
            eval_response.add_feedback((not_ans_tag, not_ans_message))
            eval_response.is_correct = False

    compare_response_and_answer(
        "HAS_VALUE", lambda: symbolic_comparison(res_converted_value, ans_converted_value, parameters)["is_correct"],
        "MISSING_VALUE", "The response is missing a value.",
        "UNEXPECTED_VALUE", "The response is expected only have unit(s), no value."
    )

    compare_response_and_answer(
        "HAS_UNIT", lambda: bool((res_converted_unit - ans_converted_unit).simplify() == 0),
        "MISSING_UNIT", "The response is missing unit(s).",
        "UNEXPECTED_UNIT", "The response is expected only have unit(s), no value."
    )

    # TODO: Comparison of units in way that allows for constructive feedback

    def check_criterion(criterion):
        criterion_tokens = criteria_parser.scan(criterion[0])
        criteria_args = []
        for token in criterion_tokens:
            if token.label == "QUANTITY":
                key = token.content.strip().lower()
                if key == "response":
                    token.content = res_parsed
                elif key == "answer":
                    token.content = ans_parsed
                else:
                    try:
                        quantity_parsed, _ = quantity_parsing(answer, units_string=units_string, strictness=strictness)
                    except Exception as e:
                        raise Exception("Could not parse quantity expression in criteria: "+str(e)) from e
                    token.content = quantity_parsed
                criteria_args.append(token.content)
        criterion_parsed = criteria_parser.parse(criterion_tokens)[0]
        def execute(node):
            key = node.label.strip()
            if key in criteria_operations.keys():
                executed_children = [execute(c) for c in node.children]
                return criteria_operations[key](executed_children)
            elif key == "QUANTITY":
                return node.content
        result = execute(criterion_parsed)
        feedback_dictionary = criterion[1]
        tag = feedback_dictionary[result][0]
        feedback = feedback_dictionary[result][1](criteria_args)
        return tag, feedback 

    for criterion in physical_quantities_criteria.items():
        tag, feedback = check_criterion(criterion)
        eval_response.add_feedback((tag,feedback))

    return eval_response

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
        "kilogrammetresecondamperes",
        "kilogram/(metre second^2)",
        "kilogram/(metresecond^2)",
        "kilograms/(meterseconds^2)",
        "10 kilogram/(metre second^2)",
        "10 kilogram/(metresecond^2)",
        "10 kilogram*metre/second**2",
        "10 kilogrammetre/second**2",
        "-10.5 kg m/s^2",
        "1 kg m/s^2 + 2 kg m/s^2",
        "10 kilogram*metre*second**(-2)",
        "10 kilogrammetresecond**(-2)",
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
        "10 g/sm",
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
        quantity, unit_latex = SLR_quantity_parsing(expr, units_string="SI", strictness="natural")
        value = quantity.value.original_string() if quantity.value is not None else None
        unit = quantity.unit.original_string() if quantity.unit is not None else None
        content = quantity.ast_root.content_string()
        print("Content: "+content)
        print("Value:   "+str(value))
        print("Unit:    "+str(unit))
        print("LaTeX:   "+str(unit_latex))
        messages = [x[1] for x in quantity.messages]
        # for criteria_tag in quantity.passed_dict:
        #     messages += [criteria.feedbacks[criteria_tag](criteria.results[criteria_tag](quantity))]
        # print("\n".join(messages))
        print(quantity.ast_root.tree_string())
    print("** COMPLETE **")
