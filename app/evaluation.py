from copy import deepcopy

from .utility.evaluation_result_utilities import EvaluationResult
from .utility.preview_utilities import parse_latex
from .context.symbolic import context as symbolic_context
from .context.physical_quantity import context as quantity_context
from .feedback.symbolic import feedback_generators as symbolic_feedback_string_generators

from collections.abc import Mapping

messages = {
    "RESERVED_EXPRESSION_MISSING": lambda label: f"Reserved expression `{label}` is not defined."
}


class FrozenValuesDictionary(dict):
    """
        A dictionary where new key:value pairs can be added,
        but changing the value for an existing key raises
        a TypeError
    """
    def __init__(self, other=None, **kwargs):
        super().__init__()
        self.update(other, **kwargs)

    def __setitem__(self, key, value):
        if key in self:
            msg = 'key {!r} already exists with value {!r}'
            raise TypeError(msg.format(key, self[key]))
        super().__setitem__(key, value)

    def update(self, other=None, **kwargs):
        if other is not None:
            for k, v in other.items() if isinstance(other, Mapping) else other:
                self[k] = v
        for k, v in kwargs.items():
            self[k] = v


def determine_context(parameters):
    if parameters.get("physical_quantity", False) is True:
        context = deepcopy(quantity_context)
    else:
        context = deepcopy(symbolic_context)

    input_symbols_reserved_codes = list(parameters.get("symbols", dict()))
    input_symbols_reserved_aliases = []

    for input_symbol in parameters.get("symbols", dict()).values():
        input_symbols_reserved_aliases += [alias for alias in input_symbol.get("aliases", []) if len(alias.strip()) > 0]

    # This code is to ensure compatibility with legacy system for defining input symbols
    for input_symbol in parameters.get("input_symbols", []):
        if len(input_symbol[0].strip()) > 0:
            input_symbols_reserved_codes.append(input_symbol[0])
            input_symbols_reserved_aliases += [ip for ip in input_symbol[1] if len(ip.strip()) > 0]

    reserved_keywords_codes = {"where", "written as"}
    reserved_keywords_aliases = {"plus_minus", "minus_plus"}
    for re in parameters["reserved_expressions_strings"].values():
        reserved_keywords_aliases = reserved_keywords_aliases.union(set(re.keys()))

    for value in parameters["reserved_expressions_strings"].values():
        reserved_keywords = reserved_keywords_aliases.union(set(value.keys()))

    reserved_keywords_codes_collisions = []
    for keyword in reserved_keywords_codes:
        if keyword in input_symbols_reserved_codes:
            reserved_keywords_codes_collisions.append(keyword)
    if len(reserved_keywords_codes_collisions) > 0:
        if len(reserved_keywords_codes_collisions) == 1:
            raise Exception("`"+"`, `".join(reserved_keywords_codes_collisions)+"` is a reserved keyword and cannot be used as an input symbol code.")
        else:
            raise Exception("`"+"`, `".join(reserved_keywords_codes_collisions)+"` are reserved keywords and cannot be used as input symbol codes.")
    reserved_keywords_aliases_collisions = []
    for keyword in reserved_keywords_aliases:
        if keyword in input_symbols_reserved_aliases:
            print("Collision found")
            reserved_keywords_aliases_collisions.append(keyword)
    if len(reserved_keywords_aliases_collisions) > 0:
        if len(reserved_keywords_aliases_collisions) == 1:
            raise Exception("`"+"`, `".join(reserved_keywords_aliases_collisions)+"` is a reserved keyword and cannot be used as an input symbol alternative.")
        else:
            raise Exception("`"+"`, `".join(reserved_keywords_aliases_collisions)+"` are reserved keywords and cannot be used as input symbol alternatives.")

    reserved_keywords = reserved_keywords_codes
    context.update({"reserved_keywords": list(reserved_keywords)})
    return context


def parse_reserved_expressions(reserved_expressions, parameters, result):
    """
    Input:
    reserved_expressions: dictionary with the following format
        {
            "learner":
                <string>: <string>,
                ...
            "task": {
                <string>: <string>,
                ...
            }
        }
    parameters: dict that contains evaluation function configuration parameters
    result: the EvaluationResult object that will hold feedback responses
    """
    parse = parameters["context"]["expression_parse"]
    preprocess = parameters["context"]["expression_preprocess"]
    parsing_parameters = deepcopy(parameters["parsing_parameters"])
    symbolic_comparison_internal_messages = symbolic_feedback_string_generators["INTERNAL"]
    reserved_expressions_dict = FrozenValuesDictionary()
    success = True
    for key in reserved_expressions.keys():
        reserved_expressions_dict.update({key: FrozenValuesDictionary()})
        for (label, expr) in reserved_expressions[key].items():
            expr_parsed = None
            preprocess_success, expr, preprocess_feedback = preprocess(key, expr, parameters)
            if preprocess_success is False:
                if key == "learner":
                    result.add_feedback(preprocess_feedback)
                    preprocess_success = True  # Preprocess can only create warnings for responses in this case
                else:
                    raise Exception(preprocess_feedback[1], preprocess_feedback[0])
            reserved_expressions[key][label] = expr
            if not isinstance(expr, str):
                raise Exception(f"Reserved expression {label} must be given as a string.")
            if len(expr.strip()) == 0:
                if key == "learner":
                    result.add_feedback(
                        (
                            f"RESERVED_EXPRESSION_MISSING_{label}",
                            messages["RESERVED_EXPRESSION_MISSING"](label)
                        )
                    )
                else:
                    raise Exception(messages["RESERVED_EXPRESSION_MISSING"](label), f"RESERVED_EXPRESSION_MISSING_{label}")
                success = False
            else:
                try:
                    expr_parsed = parse(label, expr, parsing_parameters, result)
                except Exception as e:
                    result.is_correct = False
                    success = False
                    if key == "learner":
                        result.add_feedback(
                            (
                                f"PARSE_ERROR_{label}",
                                symbolic_comparison_internal_messages("PARSE_ERROR")({'x': expr})
                            )
                        )
                    else:
                        raise Exception(symbolic_comparison_internal_messages("PARSE_ERROR")({'x': expr})) from e
            reserved_expressions_dict[key].update({label: expr_parsed})
    return success, reserved_expressions_dict


def get_criteria_string(parameters):
    criteria = parameters.get("criteria", None)
    if criteria is None:
        criteria = ",".join(parameters["context"]["default_criteria"])
    if (parameters.get("syntactical_comparison", False) is True) and ("responsewrittenasanswer" not in "".join(criteria.split())):
        criteria = criteria+", response written as answer"
    return criteria


def create_criteria_dict(criteria_parser, parsing_params):
    preprocess = parsing_params["context"]["expression_preprocess"]
    criteria_string = get_criteria_string(parsing_params)
    preprocess_success, criteria_string, preprocess_feedback = preprocess("criteria", criteria_string, parsing_params)
    if preprocess_success is False:
        raise Exception(preprocess_feedback[1], preprocess_feedback[0])
    criteria_string_list = []
    delims = [
        ("(", ")"),
        ("[", "]"),
        ("{", "}"),
    ]
    depth = {delim: 0 for delim in delims}
    delim_key = {delim[0]: delim for delim in delims}
    delim_key.update({delim[1]: delim for delim in delims})
    criterion_start = 0
    for n, c in enumerate(criteria_string):
        if c in [delim[0] for delim in delims]:
            depth[delim_key[c]] += 1
        if c in [delim[1] for delim in delims]:
            depth[delim_key[c]] -= 1
        if c == "," and all([d == 0 for d in depth.values()]):
            criteria_string_list.append(criteria_string[criterion_start:n].strip())
            criterion_start = n+1
    criteria_string_list.append(criteria_string[criterion_start:].strip())
    criteria_parsed = FrozenValuesDictionary()
    for criterion in criteria_string_list:
        try:
            criterion_tokens = criteria_parser.scan(criterion)
            criterion_parsed = criteria_parser.parse(criterion_tokens)[0]
            criteria_parsed.update({criterion_parsed.content_string(): criterion_parsed})
        except Exception as e:
            raise Exception("Cannot parse criteria: `"+criterion+"`.") from e
    return criteria_parsed


def generate_feedback(main_criteria, criteria_graphs, evaluation_parameters):
    # Generate feedback from criteria graphs
    evaluation_result = evaluation_parameters["evaluation_result"]
    response = evaluation_parameters["reserved_expressions"]["response"]
    criteria_feedback = set()
    is_correct = True
    for (criterion_identifier, graph) in criteria_graphs.items():
        # TODO: Find better way to identify main criteria for criteria graph
        main_criteria = criterion_identifier+"_TRUE"
        criteria_feedback = graph.generate_feedback(response, main_criteria)

        # TODO: Implement way to define completeness of task other than "all main criteria satisfied"
        is_correct = is_correct and main_criteria in criteria_feedback
        evaluation_result.add_criteria_graph(criterion_identifier, graph)

        # Generate feedback strings from found feedback
        # NOTE: Feedback strings are generated for each graph due to the
        #       assumption that some way to return partial feedback
        #       before script has executed completely will be available
        #       in the future
        evaluation_result.add_feedback_from_tags(criteria_feedback, graph)
    evaluation_result.is_correct = is_correct
    return


def evaluation_function(response, answer, params, include_test_data=False) -> dict:
    """
    Function that allows for various types of comparison of various kinds of expressions.
    Supported input parameters:
    strict_SI_syntax:
        - if set to True, use basic dimensional analysis functionality.
    """

    evaluation_result = EvaluationResult()
    evaluation_result.is_correct = False

    symbolic_comparison_internal_messages = symbolic_feedback_string_generators["INTERNAL"]

    parameters = deepcopy(params)

    # CONSIDER: Can this be moved into the preprocessing procedures in a consistent way?
    # Can it be turned into its own context? Or moved into the determine_context procedure?
    # What solution will be most consistently reusable?
    if parameters.get("is_latex", False):
        response = parse_latex(response, parameters.get("symbols", {}), False)

    reserved_expressions_strings = {
        "learner": {
            "response": response
        },
        "task": {
            "answer": answer
        }
    }
    parameters.update({"reserved_expressions_strings": reserved_expressions_strings})
    context = determine_context(parameters)
    default_parameters = context["default_parameters"]
    for (key, value) in default_parameters.items():
        if key not in parameters.keys():
            parameters.update({key: value})
    if "criteria" not in parameters.keys():
        parameters.update({"criteria": ",".join(context["default_criteria"])})
    try:
        preview = context["expression_preview"](response, deepcopy(parameters))["preview"]
    except Exception:
        evaluation_result.latex = response
        evaluation_result.simplified = response
    else:
        evaluation_result.latex = preview["latex"]
        evaluation_result.simplified = preview["sympy"]
    parameters.update(
        {
            "context": context,
            "parsing_parameters": context["parsing_parameters_generator"](parameters),
        }
    )

    # FIXME: Move this into expression_utilities
    if params.get("strict_syntax", True):
        if "^" in response:
            evaluation_result.add_feedback(("NOTATION_WARNING_EXPONENT", symbolic_comparison_internal_messages("NOTATION_WARNING_EXPONENT")(dict())))
        if "!" in response:
            evaluation_result.add_feedback(("NOTATION_WARNING_FACTORIAL", symbolic_comparison_internal_messages("NOTATION_WARNING_FACTORIAL")(dict())))

    reserved_expressions_success, reserved_expressions = parse_reserved_expressions(reserved_expressions_strings, parameters, evaluation_result)
    if reserved_expressions_success is False:
        return evaluation_result.serialise(include_test_data)
    reserved_expressions_parsed = {**reserved_expressions["learner"], **reserved_expressions["task"]}
    parameters.update({"reserved_keywords": parameters["context"]["reserved_keywords"]+list(reserved_expressions_parsed.keys())})

    criteria_parser = context["generate_criteria_parser"](reserved_expressions)
    criteria = create_criteria_dict(criteria_parser, parameters)

    parsing_parameters = parameters["context"]["parsing_parameters_generator"](parameters, unsplittable_symbols=list(reserved_expressions_parsed.keys()))

    evaluation_parameters = FrozenValuesDictionary(
        {
            "reserved_expressions_strings": reserved_expressions_strings,
            "reserved_expressions": reserved_expressions_parsed,
            "criteria": criteria,
            "disabled_evaluation_nodes": parameters.get("disabled_evaluation_nodes", set()),
            "evaluation_result": evaluation_result,
            "parsing_parameters": parsing_parameters,
            "evaluation_result": evaluation_result,
            "syntactical_comparison": parameters.get("syntactical_comparison", False),
            "multiple_answers_criteria": parameters.get("multiple_answers_criteria", "all"),
            "numerical": parameters.get("numerical", False),
            "atol": parameters.get("atol", 0),
            "rtol": parameters.get("rtol", 0),
        }
    )

    # Performs evaluation of response
    feedback_procedures = parameters["context"]["feedback_procedure_generator"](evaluation_parameters)
    generate_feedback(criteria, feedback_procedures, evaluation_parameters)

    result = evaluation_result.serialise(include_test_data)

    if parameters.get("feedback_for_incorrect_response", None) is not None:
        result["feedback"] = parameters["feedback_for_incorrect_response"]

    return result
