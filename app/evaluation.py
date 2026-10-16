from __future__ import annotations

from collections.abc import Collection, Iterable, Mapping
from copy import deepcopy
from typing import Any

from lambdafeedback.criteria import CriteriaGraph
from lambdafeedback.slr_parsing import SLRParser
from lambdafeedback.expression_parsing import (
    AbsoluteValueNotationError,
    BracketNotationError,
    ExpressionParams,
    parse_latex,
)

from app.context.physical_quantity import context as quantity_context
from app.context.symbolic import context as symbolic_context
from app.feedback.symbolic import feedback_generators as symbolic_feedback_string_generators, internal_feedback
from app.feedback.tags import FeedbackTag, FeedbackTagName
from app.frozen_dict import FrozenValuesDictionary
from app.result import EvaluationResult
from app.types import Parameters

messages = {
    "RESERVED_EXPRESSION_MISSING": lambda label: f"Reserved expression `{label}` is not defined."
}


def notation_error_feedback(error: BracketNotationError | AbsoluteValueNotationError, original_text: str) -> FeedbackTag:
    """`FeedbackTag` for a `BracketNotationError`/`AbsoluteValueNotationError` raised while preprocessing."""
    if isinstance(error, BracketNotationError):
        return FeedbackTag(FeedbackTagName.BRACKET_NOTATION_MISMATCH, {"x": original_text})
    return FeedbackTag(FeedbackTagName.ABSOLUTE_VALUE_NOTATION_AMBIGUITY, {"name": error.name})


def _input_symbol_codes_and_aliases(parameters: Parameters) -> tuple[list[str], list[str]]:
    """The codes and (non-empty) aliases of the input symbols, from both `symbols` and the legacy `input_symbols`."""
    codes = list(parameters.get("symbols", dict()))
    aliases = []

    for input_symbol in parameters.get("symbols", dict()).values():
        aliases += [alias for alias in input_symbol.get("aliases", []) if len(alias.strip()) > 0]

    # This code is to ensure compatibility with legacy system for defining input symbols
    for input_symbol in parameters.get("input_symbols", []):
        if len(input_symbol[0].strip()) > 0:
            codes.append(input_symbol[0])
            aliases += [ip for ip in input_symbol[1] if len(ip.strip()) > 0]

    return codes, aliases


def _raise_on_collisions(keywords: Iterable[str], symbols: Collection[str], kind: str) -> None:
    """Raises if any of `keywords` is used as an input symbol `kind` (e.g. "code" or "alternative")."""
    collisions = sorted(keyword for keyword in keywords if keyword in symbols)
    if len(collisions) == 1:
        raise Exception("`"+"`, `".join(collisions)+f"` is a reserved keyword and cannot be used as an input symbol {kind}.")
    elif len(collisions) > 1:
        raise Exception("`"+"`, `".join(collisions)+f"` are reserved keywords and cannot be used as input symbol {kind}s.")


def determine_context(parameters: Parameters) -> dict[str, Any]:
    if parameters.get("physical_quantity", False) is True:
        context = deepcopy(quantity_context)
    else:
        context = deepcopy(symbolic_context)

    input_symbols_reserved_codes, input_symbols_reserved_aliases = _input_symbol_codes_and_aliases(parameters)

    reserved_keywords_codes = {"where", "written as", "contains", "proportional to"}
    reserved_keywords_aliases = {"plus_minus", "minus_plus"}
    for expressions in parameters["reserved_expressions_strings"].values():
        reserved_keywords_aliases = reserved_keywords_aliases.union(set(expressions.keys()))

    _raise_on_collisions(reserved_keywords_codes, input_symbols_reserved_codes, "code")
    _raise_on_collisions(reserved_keywords_aliases, input_symbols_reserved_aliases, "alternative")

    context.update({"reserved_keywords": list(reserved_keywords_codes)})
    return context


def parse_reserved_expressions(
    reserved_expressions: dict[str, dict[str, str]], parameters: Parameters, result: EvaluationResult
) -> tuple[bool, FrozenValuesDictionary]:
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
            original_expr = expr
            try:
                expr = preprocess(key, expr, parameters)
            except (BracketNotationError, AbsoluteValueNotationError) as e:
                feedback = notation_error_feedback(e, original_expr)
                expr = e.expression
                if key == "learner":
                    # Preprocess can only create warnings for responses in this case
                    result.add_feedback(str(feedback.tag), internal_feedback(feedback))
                else:
                    raise Exception(internal_feedback(feedback), str(feedback.tag)) from e
            reserved_expressions[key][label] = expr
            if not isinstance(expr, str):
                raise Exception(f"Reserved expression {label} must be given as a string.")
            if len(expr.strip()) == 0:
                if key == "learner":
                    result.add_feedback(
                        f"RESERVED_EXPRESSION_MISSING_{label}",
                        messages["RESERVED_EXPRESSION_MISSING"](label)
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
                            f"PARSE_ERROR_{label}",
                            symbolic_comparison_internal_messages("PARSE_ERROR")({'x': expr})
                        )
                    else:
                        raise Exception(symbolic_comparison_internal_messages("PARSE_ERROR")({'x': expr})) from e
            reserved_expressions_dict[key].update({label: expr_parsed})
    return success, reserved_expressions_dict


def get_criteria_string(parameters: Parameters) -> str:
    criteria = parameters.get("criteria", None)
    if criteria is None:
        criteria = ",".join(parameters["context"]["default_criteria"])
    if (parameters.get("syntactical_comparison", False) is True) and ("responsewrittenasanswer" not in "".join(criteria.split())):
        criteria = criteria+", response written as answer"
    return criteria


def split_criteria(criteria_string: str) -> list[str]:
    """Splits `criteria_string` on the commas that are not inside brackets, and strips each criterion."""
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
    return criteria_string_list


def create_criteria_dict(criteria_parser: SLRParser, parameters: Parameters) -> FrozenValuesDictionary:
    preprocess = parameters["context"]["expression_preprocess"]
    original_criteria_string = get_criteria_string(parameters)
    try:
        criteria_string = preprocess("criteria", original_criteria_string, parameters)
    except (BracketNotationError, AbsoluteValueNotationError) as e:
        feedback = notation_error_feedback(e, original_criteria_string)
        raise Exception(internal_feedback(feedback), str(feedback.tag)) from e
    criteria_parsed = FrozenValuesDictionary()
    for criterion in split_criteria(criteria_string):
        try:
            criterion_tokens = criteria_parser.scan(criterion)
            criterion_parsed = criteria_parser.parse(criterion_tokens)[0]
            criteria_parsed.update({criterion_parsed.content_string(): criterion_parsed})
        except Exception as e:
            raise Exception("Cannot parse criteria: `"+criterion+"`.") from e
    return criteria_parsed


def _disable_evaluation_nodes(graph: CriteriaGraph, disabled_evaluation_nodes: Collection[str]) -> None:
    """Makes each evaluation in `disabled_evaluation_nodes` skip straight to the end of `graph`."""
    for evaluation in graph.evaluations.values():
        if evaluation.label in disabled_evaluation_nodes:
            evaluation.replacement = CriteriaGraph.END_LABEL


def generate_feedback(criteria_graphs: Mapping[str, CriteriaGraph], evaluation_parameters: Parameters) -> None:
    # Generate feedback from criteria graphs
    evaluation_result = evaluation_parameters["evaluation_result"]
    response = evaluation_parameters["reserved_expressions"]["response"]
    is_correct = True
    custom_feedback = evaluation_parameters.get("custom_feedback", {})
    for (criterion_identifier, graph) in criteria_graphs.items():
        # TODO: Find better way to identify main criteria for criteria graph
        main_criteria = criterion_identifier+"_TRUE"
        criteria_feedback = graph.generate_feedback(response, main_criteria)

        # TODO: Implement way to define completeness of task other than "all main criteria satisfied"
        is_correct = is_correct and main_criteria in criteria_feedback
        evaluation_result.criteria_graphs[criterion_identifier] = graph

        # Generate feedback strings from found feedback
        # NOTE: Feedback strings are generated for each graph due to the
        #       assumption that some way to return partial feedback
        #       before script has executed completely will be available
        #       in the future
        graph.export_feedback(evaluation_result, criteria_feedback, custom_feedback=custom_feedback)
    evaluation_result.is_correct = is_correct
    return


def _apply_tolerance_aliases(params: dict[str, Any]) -> None:
    """Copies `relative_tolerance`/`absolute_tolerance` to `rtol`/`atol` in `params`."""
    if "relative_tolerance" in params:
        params["rtol"] = params["relative_tolerance"]

    if "absolute_tolerance" in params:
        params["atol"] = params["absolute_tolerance"]


def _build_parameters(params: dict[str, Any], response: str, answer: str) -> dict[str, Any]:
    """
    A copy of `params` completed with the context's defaults, the reserved expressions
    (with `response` read as LaTeX if `is_latex` is set), the context and the parsing parameters.
    """
    parameters = deepcopy(params)

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

    reserved_expressions_keys = list(reserved_expressions_strings["learner"].keys())+list(reserved_expressions_strings["task"].keys())
    parameters.update(
        {
            "context": context,
            "reserved_keywords": context["reserved_keywords"]+reserved_expressions_keys,
        }
    )
    parsing_parameters = context["parsing_parameters_generator"](parameters, unsplittable_symbols=reserved_expressions_keys)
    parameters.update(
        {
            "parsing_parameters": parsing_parameters,
        }
    )

    # CONSIDER: Can this be moved into the preprocessing procedures in a consistent way?
    # Can it be turned into its own context? Or moved into the determine_context procedure?
    # What solution will be most consistently reusable?
    if parameters.get("is_latex", False):
        parameters["reserved_expressions_strings"]["learner"].update(
            {
                "response": parse_latex(response, ExpressionParams.from_dict(parameters).symbols),
            }
        )
    return parameters


def notation_warnings(response: str, strict_syntax: bool) -> list[str]:
    """The tags of the notation warnings for `response`."""
    # FIXME: Move these notation warnings into lambdafeedback.expression_parsing
    tags = []
    if strict_syntax:
        if "^" in response:
            tags.append("NOTATION_WARNING_EXPONENT")
        if "!" in response:
            tags.append("NOTATION_WARNING_FACTORIAL")
    if "!!!" in response:
        tags.append("NOTATION_WARNING_TRIPLE_FACTORIAL")
    return tags


def _add_notation_warnings(evaluation_result: EvaluationResult, response: str, params: Parameters) -> None:
    symbolic_comparison_internal_messages = symbolic_feedback_string_generators["INTERNAL"]
    for tag in notation_warnings(response, params.get("strict_syntax", False)):
        evaluation_result.add_feedback(tag, symbolic_comparison_internal_messages(tag)(dict()))


def _set_preview_fields(
    evaluation_result: EvaluationResult, response: str, parameters: Parameters, reserved_expressions: Mapping[str, Mapping[str, Any]]
) -> None:
    """Sets the `latex` and `simplified` forms of the response on `evaluation_result`."""
    try:
        preview = parameters["context"]["expression_preview"](response, deepcopy(parameters))["preview"]
    except Exception:
        evaluation_result.latex = response
        evaluation_result.simplified = response
    else:
        evaluation_result.latex = preview["latex"]
        parsed_response = reserved_expressions["learner"]["response"]
        if isinstance(parsed_response, list) or isinstance(parsed_response, set):
            evaluation_result.simplified = ", ".join([str(ex.simplify()) for ex in parsed_response])
        else:
            try:
                evaluation_result.simplified = str(parsed_response.simplify())
            except Exception:
                evaluation_result.simplified = response


def _build_evaluation_parameters(
    parameters: Parameters, reserved_expressions: Mapping[str, Mapping[str, Any]], criteria: Mapping[str, Any], evaluation_result: EvaluationResult
) -> FrozenValuesDictionary:
    return FrozenValuesDictionary(
        {
            "reserved_expressions_strings": parameters["reserved_expressions_strings"],
            "reserved_expressions": {**reserved_expressions["learner"], **reserved_expressions["task"]},
            "criteria": criteria,
            "disabled_evaluation_nodes": parameters.get("disabled_evaluation_nodes", set()),
            "parsing_parameters": parameters["parsing_parameters"],
            "evaluation_result": evaluation_result,
            "multiple_answers_criteria": parameters.get("multiple_answers_criteria", "all"),
            "numerical": parameters.get("numerical", False),
            "atol": parameters.get("atol", 0),
            "rtol": parameters.get("rtol", 0),
            "custom_feedback": parameters.get("custom_feedback", {}),
        }
    )


def evaluation_function(response: str, answer: str, params: dict[str, Any], include_test_data: bool = False) -> dict[str, Any]:
    """
    Function that allows for various types of comparison of various kinds of expressions.
    Supported input parameters:
    strict_SI_syntax:
        - if set to True, use basic dimensional analysis functionality.
    """
    _apply_tolerance_aliases(params)

    evaluation_result = EvaluationResult()
    evaluation_result.is_correct = False

    parameters = _build_parameters(params, response, answer)
    context = parameters["context"]

    _add_notation_warnings(evaluation_result, response, params)

    reserved_expressions_success, reserved_expressions = parse_reserved_expressions(
        parameters["reserved_expressions_strings"], parameters, evaluation_result
    )
    if reserved_expressions_success is False:
        return evaluation_result.serialise(include_test_data)

    _set_preview_fields(evaluation_result, response, parameters, reserved_expressions)

    criteria_parser = context["generate_criteria_parser"](reserved_expressions)
    criteria = create_criteria_dict(criteria_parser, parameters)

    evaluation_parameters = _build_evaluation_parameters(parameters, reserved_expressions, criteria, evaluation_result)

    # Performs evaluation of response
    feedback_procedures = context["feedback_procedure_generator"](evaluation_parameters)
    for graph in feedback_procedures.values():
        _disable_evaluation_nodes(graph, evaluation_parameters["disabled_evaluation_nodes"])
    generate_feedback(feedback_procedures, evaluation_parameters)

    result = evaluation_result.serialise(include_test_data)

    if parameters.get("feedback_for_incorrect_response", None) is not None:
        result["feedback"] = parameters["feedback_for_incorrect_response"]

    return result
