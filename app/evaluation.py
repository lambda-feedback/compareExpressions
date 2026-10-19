from __future__ import annotations

import json
import logging
import os
import time
import traceback
import uuid
from collections.abc import Collection, Iterable, Mapping
from copy import deepcopy
from typing import Any

from lambdafeedback.criteria import CriteriaGraph, CriteriaSyntaxError, split_criteria
from lambdafeedback.slr_parsing import ExprNode, SLRParser
from lambdafeedback.expression_parsing import (
    AbsoluteValueNotationError,
    BracketNotationError,
    ExpressionParams,
    notation_warnings,
    parse_latex,
)

from app.context.base import Context
from app.context.physical_quantity import context as quantity_context
from app.context.symbolic import context as symbolic_context
from app.context.symbolic.comparison import is_inequality_or_boolean
from app.feedback.symbolic import feedback_generators as symbolic_feedback_string_generators, internal_feedback
from app.feedback.tags import FeedbackTag, FeedbackTagName
from app.evaluation_parameters import EvaluationParameters
from app.result import EvaluationResult
from app.types import Parameters

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


class TaskConfigurationError(Exception):
    """
    Raised for problems with the task setup (params, answer, criteria) or the shape of the request.
    These are passed on unchanged by `evaluation_function`.
    NOTE: The message must never contain the response.
    """


class ResponseParsingError(ValueError):
    """
    Raised when the response cannot be parsed.
    Subclasses ValueError so that the base layer returns it as an unprocessable submission (HTTP 422).
    These are passed on unchanged by `evaluation_function`.
    NOTE: The message must never contain the response.
    """


class EvaluationError(Exception):
    """
    Generic error raised by `evaluation_function` in place of any unexpected
    exception, since their messages can contain the response.
    """


messages = {
    "RESERVED_EXPRESSION_MISSING": lambda label: f"Reserved expression `{label}` is not defined.",
    "RESERVED_EXPRESSION_INEQUALITY": lambda label: (
        f"Reserved expression `{label}` is an inequality or evaluates to true/false, which is not supported."
    )
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
        raise TaskConfigurationError("`" + "`, `".join(collisions) + f"` is a reserved keyword and cannot be used as an input symbol {kind}.")
    elif len(collisions) > 1:
        raise TaskConfigurationError("`" + "`, `".join(collisions) + f"` are reserved keywords and cannot be used as input symbol {kind}s.")


def select_context(parameters: Parameters) -> Context:
    """The physical quantity context if `physical_quantity` is set, otherwise the symbolic context."""
    if parameters.get("physical_quantity", False) is True:
        return quantity_context
    return symbolic_context


def _reserved_keywords(parameters: Parameters) -> list[str]:
    """
    The keywords reserved by the criteria grammar.
    Raises if a reserved keyword or reserved expression name is used as an input symbol.
    """
    input_symbols_reserved_codes, input_symbols_reserved_aliases = _input_symbol_codes_and_aliases(parameters)

    reserved_keywords_codes = {"where", "written as", "contains", "proportional to"}
    reserved_keywords_aliases = {"plus_minus", "minus_plus"}
    for expressions in parameters["reserved_expressions_strings"].values():
        reserved_keywords_aliases = reserved_keywords_aliases.union(set(expressions.keys()))

    _raise_on_collisions(reserved_keywords_codes, input_symbols_reserved_codes, "code")
    _raise_on_collisions(reserved_keywords_aliases, input_symbols_reserved_aliases, "alternative")

    return list(reserved_keywords_codes)


def _report(
    key: str, result: EvaluationResult, tag: str, message: str | None, error: Exception, cause: Exception | None = None
) -> None:
    """
    Reports a problem with a reserved expression: for a learner expression it is added to `result` as feedback,
    for a task expression it is an error in the task, so `error` is raised (from `cause`).
    """
    if key == "learner":
        result.add_feedback(tag, message)
    elif cause is None:
        raise error
    else:
        raise error from cause


def parse_reserved_expressions(
    context: Context, reserved_expressions: dict[str, dict[str, str]], parameters: Parameters, result: EvaluationResult
) -> tuple[bool, dict[str, dict[str, Any]]]:
    """
    Input:
    context: the context used to preprocess and parse the expressions
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
    parse = context.expression_parse
    preprocess = context.expression_preprocess
    parsing_parameters = deepcopy(parameters["parsing_parameters"])
    symbolic_comparison_internal_messages = symbolic_feedback_string_generators["INTERNAL"]
    reserved_expressions_dict: dict[str, dict[str, Any]] = {}
    success = True
    for key in reserved_expressions.keys():
        reserved_expressions_dict.update({key: {}})
        for (label, expr) in reserved_expressions[key].items():
            expr_parsed = None
            original_expr = expr
            try:
                expr = preprocess(key, expr, parameters)
            except (BracketNotationError, AbsoluteValueNotationError) as e:
                feedback = notation_error_feedback(e, original_expr)
                expr = e.expression
                # Preprocess can only create warnings for responses in this case
                tag = str(feedback.tag)
                message = internal_feedback(feedback)
                _report(key, result, tag, message, TaskConfigurationError(message, tag), cause=e)
            reserved_expressions[key][label] = expr
            if not isinstance(expr, str):
                raise TaskConfigurationError(f"Reserved expression {label} must be given as a string.")
            if len(expr.strip()) == 0:
                tag = f"RESERVED_EXPRESSION_MISSING_{label}"
                message = messages["RESERVED_EXPRESSION_MISSING"](label)
                _report(key, result, tag, message, TaskConfigurationError(message, tag))
                success = False
            else:
                try:
                    expr_parsed = parse(label, expr, parsing_parameters, result)
                except Exception as e:
                    result.is_correct = False
                    success = False
                    message = symbolic_comparison_internal_messages("PARSE_ERROR")({'x': expr})
                    # The error for a task expression has no tag
                    _report(key, result, f"PARSE_ERROR_{label}", message, TaskConfigurationError(message), cause=e)
                if key == "task" and is_inequality_or_boolean(expr_parsed):
                    raise TaskConfigurationError(
                        messages["RESERVED_EXPRESSION_INEQUALITY"](label),
                        f"RESERVED_EXPRESSION_INEQUALITY_{label}"
                    )
            reserved_expressions_dict[key].update({label: expr_parsed})
    return success, reserved_expressions_dict


def get_criteria_string(context: Context, parameters: Parameters) -> str:
    criteria = parameters.get("criteria", None)
    if criteria is None:
        criteria = ",".join(context.default_criteria)
    if (parameters.get("syntactical_comparison", False) is True) and ("responsewrittenasanswer" not in "".join(criteria.split())):
        criteria = criteria + ", response written as answer"
    return criteria


def create_criteria_dict(context: Context, criteria_parser: SLRParser, parameters: Parameters) -> dict[str, ExprNode]:
    preprocess = context.expression_preprocess
    original_criteria_string = get_criteria_string(context, parameters)
    try:
        criteria_string = preprocess("criteria", original_criteria_string, parameters)
    except (BracketNotationError, AbsoluteValueNotationError) as e:
        feedback = notation_error_feedback(e, original_criteria_string)
        raise TaskConfigurationError(internal_feedback(feedback), str(feedback.tag)) from e
    try:
        criteria_string_list = split_criteria(criteria_string)
    except CriteriaSyntaxError as e:
        raise TaskConfigurationError("Cannot parse criteria: `" + criteria_string + "`.") from e
    criteria_parsed: dict[str, ExprNode] = {}
    for criterion in criteria_string_list:
        try:
            criterion_tokens = criteria_parser.scan(criterion)
            criterion_parsed = criteria_parser.parse(criterion_tokens)[0]
            # A criterion that is given twice cannot be parsed
            if criterion_parsed.content_string() in criteria_parsed:
                raise TypeError(f"criterion {criterion_parsed.content_string()!r} is given more than once")
            criteria_parsed.update({criterion_parsed.content_string(): criterion_parsed})
        except Exception as e:
            raise TaskConfigurationError("Cannot parse criteria: `" + criterion + "`.") from e
    return criteria_parsed


def _disable_evaluation_nodes(graph: CriteriaGraph, disabled_evaluation_nodes: Collection[str]) -> None:
    """Makes each evaluation in `disabled_evaluation_nodes` skip straight to the end of `graph`."""
    for evaluation in graph.evaluations.values():
        if evaluation.label in disabled_evaluation_nodes:
            evaluation.replacement = CriteriaGraph.END_LABEL


def generate_feedback(criteria_graphs: Mapping[str, CriteriaGraph], evaluation_parameters: EvaluationParameters) -> None:
    # Generate feedback from criteria graphs
    evaluation_result = evaluation_parameters.evaluation_result
    response = evaluation_parameters.reserved_expressions["response"]
    is_correct = True
    custom_feedback = evaluation_parameters.custom_feedback
    for (criterion_identifier, graph) in criteria_graphs.items():
        # TODO: Find better way to identify main criteria for criteria graph
        main_criteria = criterion_identifier + "_TRUE"
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


def _build_parameters(context: Context, params: dict[str, Any], response: str, answer: str) -> dict[str, Any]:
    """
    A copy of `params` completed with the context's defaults, the reserved expressions,
    the reserved keywords and the parsing parameters.
    """
    parameters = deepcopy(params)
    # Applied to the copy, so the caller's `params` keep only what they set
    _apply_tolerance_aliases(parameters)

    reserved_expressions_strings = {
        "learner": {
            "response": response
        },
        "task": {
            "answer": answer
        }
    }
    parameters.update({"reserved_expressions_strings": reserved_expressions_strings})
    reserved_keywords = _reserved_keywords(parameters)
    for (key, value) in context.default_parameters.items():
        if key not in parameters.keys():
            parameters.update({key: value})
    if "criteria" not in parameters.keys():
        parameters.update({"criteria": ",".join(context.default_criteria)})

    reserved_expressions_keys = list(reserved_expressions_strings["learner"].keys()) + list(reserved_expressions_strings["task"].keys())
    parameters.update(
        {
            "reserved_keywords": reserved_keywords + reserved_expressions_keys,
        }
    )
    parsing_parameters = context.parsing_parameters_generator(parameters, unsplittable_symbols=reserved_expressions_keys)
    parameters.update(
        {
            "parsing_parameters": parsing_parameters,
        }
    )
    return parameters


# CONSIDER: Can this be moved into the preprocessing procedures in a consistent way?
# Can it be turned into its own context? Or moved into the select_context procedure?
# What solution will be most consistently reusable?
def _parse_latex_response(parameters: dict[str, Any], response: str) -> None:
    """Replaces the response in the reserved expressions of `parameters` with its LaTeX read as SymPy syntax."""
    try:
        response_parsed = parse_latex(response, ExpressionParams.from_dict(parameters).symbols)
    except ValueError:
        # `from None` stops the original exception, and its message (which can contain the response), being chained onto this one
        raise ResponseParsingError("Failed to parse LaTeX expression") from None
    parameters["reserved_expressions_strings"]["learner"].update(
        {
            "response": response_parsed,
        }
    )


def _add_notation_warnings(evaluation_result: EvaluationResult, response: str, params: Parameters) -> None:
    symbolic_comparison_internal_messages = symbolic_feedback_string_generators["INTERNAL"]
    for warning in notation_warnings(response, bool(params.get("strict_syntax", False))):
        evaluation_result.add_feedback(str(warning), symbolic_comparison_internal_messages(str(warning))(dict()))


def _set_preview_fields(
    context: Context, evaluation_result: EvaluationResult, response: str, parameters: Parameters,
    reserved_expressions: Mapping[str, Mapping[str, Any]]
) -> None:
    """Sets the `latex` and `simplified` forms of the response on `evaluation_result`."""
    try:
        preview = context.expression_preview(response, deepcopy(parameters))["preview"]
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
    parameters: Parameters, reserved_expressions: Mapping[str, Mapping[str, Any]], criteria: Mapping[str, ExprNode],
    evaluation_result: EvaluationResult
) -> EvaluationParameters:
    return EvaluationParameters(
        reserved_expressions_strings=parameters["reserved_expressions_strings"],
        reserved_expressions={**reserved_expressions["learner"], **reserved_expressions["task"]},
        criteria=criteria,
        disabled_evaluation_nodes=parameters.get("disabled_evaluation_nodes", set()),
        parsing_parameters=parameters["parsing_parameters"],
        evaluation_result=evaluation_result,
        multiple_answers_criteria=parameters.get("multiple_answers_criteria", "all"),
        numerical=parameters.get("numerical", False),
        atol=parameters.get("atol", 0),
        rtol=parameters.get("rtol", 0),
        custom_feedback=parameters.get("custom_feedback", {}),
    )


def log_event(event: str, eval_id: str, level: int = logging.INFO, **fields: Any) -> None:
    """
    Writes a single JSON line so that logs can be filtered with CloudWatch Logs Insights.
    NOTE: Never pass user data (e.g. the response) or anything derived from it.
    """
    logger.log(level, json.dumps({"event": event, "eval_id": eval_id, **fields}, default=str))


def elapsed_ms(start_time: float) -> float:
    return round((time.perf_counter() - start_time) * 1000, 1)


def traceback_frames(exception: BaseException) -> list[str]:
    """
    Returns the location of each frame in the traceback without the exception messages,
    since these can contain the response.
    """
    return [f"{os.path.basename(frame.filename)}:{frame.lineno} in {frame.name}" for frame in traceback.extract_tb(exception.__traceback__)]


def evaluation_function(response: str, answer: str, params: dict[str, Any], include_test_data: bool = False) -> dict[str, Any]:
    """
    Function that allows for various types of comparison of various kinds of expressions.
    Supported input parameters:
    strict_SI_syntax:
        - if set to True, use basic dimensional analysis functionality.

    Logs the start, each stage and the end (or error) of the evaluation.
    No user data is logged: the response, and exception messages and
    tracebacks (which can contain the response), are left out.
    For the same reason, any exception other than a TaskConfigurationError
    or ResponseParsingError is replaced by a generic EvaluationError.
    """
    eval_id = uuid.uuid4().hex[:8]
    start_time = time.perf_counter()
    stage: dict[str, Any] = {"name": "setup", "eval_id": eval_id, "start_time": start_time, "early_return": False}

    log_event(
        "evaluation_start",
        eval_id,
        params=params,
        answer=answer,
        include_test_data=include_test_data,
    )

    try:
        result = _evaluate(response, answer, params, include_test_data, stage)
    except Exception as e:
        log_event(
            "evaluation_error",
            eval_id,
            level=logging.ERROR,
            stage=stage["name"],
            duration_ms=elapsed_ms(start_time),
            error_type=type(e).__name__,
            cause_type=type(e.__cause__).__name__ if e.__cause__ is not None else None,
            traceback=traceback_frames(e),
        )
        if isinstance(e, (TaskConfigurationError, ResponseParsingError)):
            raise
        # `from None` stops the original exception, and its message, being chained onto this one
        raise EvaluationError(f"Evaluation failed during stage `{stage['name']}` ({type(e).__name__}). Reference: {eval_id}") from None

    log_event(
        "evaluation_end",
        eval_id,
        is_correct=result.get("is_correct"),
        duration_ms=elapsed_ms(start_time),
        early_return=stage["early_return"],
    )
    return result


def _evaluate(
    response: str, answer: str, params: dict[str, Any], include_test_data: bool, stage: dict[str, Any]
) -> dict[str, Any]:
    def enter_stage(name: str) -> None:
        stage["name"] = name
        log_event("stage_start", stage["eval_id"], stage=name, elapsed_ms=elapsed_ms(stage["start_time"]))

    evaluation_result = EvaluationResult()
    evaluation_result.is_correct = False

    enter_stage("determine_context")
    context = select_context(params)
    parameters = _build_parameters(context, params, response, answer)

    if parameters.get("is_latex", False):
        enter_stage("parse_latex")
        _parse_latex_response(parameters, response)

    _add_notation_warnings(evaluation_result, response, params)

    enter_stage("parse_reserved_expressions")
    reserved_expressions_success, reserved_expressions = parse_reserved_expressions(
        context, parameters["reserved_expressions_strings"], parameters, evaluation_result
    )
    if reserved_expressions_success is False:
        stage["early_return"] = True
        return evaluation_result.serialise(include_test_data)

    enter_stage("preview")
    _set_preview_fields(context, evaluation_result, response, parameters, reserved_expressions)

    enter_stage("parse_criteria")
    criteria_parser = context.generate_criteria_parser(reserved_expressions)
    criteria = create_criteria_dict(context, criteria_parser, parameters)

    evaluation_parameters = _build_evaluation_parameters(parameters, reserved_expressions, criteria, evaluation_result)

    # Performs evaluation of response
    enter_stage("generate_feedback_procedures")
    feedback_procedures = context.feedback_procedure_generator(evaluation_parameters)
    for graph in feedback_procedures.values():
        _disable_evaluation_nodes(graph, evaluation_parameters.disabled_evaluation_nodes)
    enter_stage("generate_feedback")
    generate_feedback(feedback_procedures, evaluation_parameters)

    enter_stage("serialise")
    result = evaluation_result.serialise(include_test_data)

    if parameters.get("feedback_for_incorrect_response", None) is not None:
        result["feedback"] = parameters["feedback_for_incorrect_response"]

    return result
