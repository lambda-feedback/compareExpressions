from .evaluation_response_utilities import EvaluationResponse
from .symbolic_comparison_evaluation import evaluation_function as symbolic_comparison
from .slr_quantity import quantity_comparison
from .preview import preview_function

## Imports for top-down mockup-of restructuring
from .criteria_parsing import generate_criteria_parser
from .symbolic import parse as symbolic_parse
from .physical_quantity import parse as quantity_parse
from .criteria_graph_utilities import CriteriaGraph
## End of imports for top-down mockup-of restructuring

from collections.abc import Mapping
from sympy import Basic

class FrozenValuesDictionary(dict):
    """
        A dictionary where new key:value pairs can be added,
        but changng the value for an existing key raises
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

def parse_reserved_expressions(reserved_expressions, parameters):
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
    """
    reserved_expressions_dict = FrozenValuesDictionary()
    if parameters.get("physical_quantity", False) is True:
        parse = quantity_parse
    else:
        parse = symbolic_parse
    parse = lambda expr: parse(expr, parameters)
    return reserved_expressions_dict.update({key: parse(key, value) for (key, value) in reserved_expressions})

def get_criteria(parameters):
    criteria = parameters.get("criteria", None)
    if criteria is None:
        if parameters.get("physical_quantity", False) is True:
            parse = quantity_default_criteria
        else:
            parse = symbolic_default_criteria

def generate_feedback(main_criteria, criteria_graphs, evaluation_parameters):
    # Generate feedback from criteria graphs
    eval_response = evaluation_parameters["eval_response"]
    criteria_feedback = set()
    for (criterion_identifier, graph) in criteria_graphs.items():
        # TODO: Find better way to identify main criteria for criteria graph
        main_criteria = criterion_identifier+"_TRUE"
        criteria_feedback = criteria_feedback.union(graph.generate_feedback(response, main_criteria))

        # TODO: Implement way to define completeness of task other than "all main criteria satisfied"
        is_correct = is_correct and main_criteria in criteria_feedback
        eval_response.add_criteria_graph(criterion_identifier, graph)

        # Generate feedback strings from found feedback
        # NOTE: Feedback strings are generated for each graph due to the
        #       assumption that some way to return partial feedback
        #       before script has executed completely will be available
        #       in the future
        eval_response.add_feedback_from_tags(criteria_feedback, graph, {"criterion": criteria_parsed[criterion_identifier]})
        result = main_criteria in criteria_feedback
        for item in criteria_feedback:
            eval_response.add_feedback((item, ""))
        for (reference_tag, reference_strings) in reference_criteria_strings.items():
            if reference_tag in eval_response.get_tags():
                continue
            if "".join(criterion_identifier.split()) in reference_strings:
                feedback = symbolic_comparison_criteria[reference_tag].feedback[result]([])
                eval_response.add_feedback((reference_tag, feedback))
                break
    return


def evaluation_function(response, answer, params, include_test_data=False) -> dict:
    """
    Function that allows for various types of comparison of various kinds of expressions.
    Supported input parameters:
    strict_SI_syntax:
        - if set to True, use basic dimensional analysis functionality.
    """

    ## TODO: Top-down restructuring in progress, code below is not yet functional
    reserved_expressions = {
        "learner": {
            "response": response
        }
        "task": {
            "answer": answer
        }
    }
    reserved_expressions_parsed

    criteria = get_criteria(parameters)

    eval_response = EvaluationResponse()
    eval_response.is_correct = False

    evaluation_parameters = FrozenValuesDictionary(
        {
            "reserved_expressions": reserved_expressions_parsed,
            "disabled_evaluation_nodes": params.get("disabled_evaluation_nodes", set()),
        }
    )

    generate_feedback(main_criteria, criteria_graphs, evaluation_parameters)
    ## TODO: Top-down restructuring in progress, code aboce is not yet functional

    input_symbols_reserved_words = list(params.get("symbols", dict()).keys())

    for input_symbol in params.get("symbols", dict()).values():
        input_symbols_reserved_words += input_symbol.get("aliases",[])

    for input_symbol in params.get("input_symbols", []):
        input_symbols_reserved_words += [input_symbol[0]]+input_symbol[1]

    reserved_keywords = ["response", "answer", "plus_minus", "minus_plus", "where"]
    reserved_keywords_collisions = []
    for keyword in reserved_keywords:
        if keyword in input_symbols_reserved_words:
            reserved_keywords_collisions.append(keyword)
    if len(reserved_keywords_collisions) > 0:
        raise Exception("`"+"`, `".join(reserved_keywords_collisions)+"` are reserved keyword and cannot be used as input symbol codes or alternatives.")

    parameters = {
        "comparison": "expression",
        "strict_syntax": True,
        "reserved_keywords": reserved_keywords,
    }
    parameters.update(params)

    if params.get("is_latex", False):
        response = preview_function(response, params)["preview"]["sympy"]

    reserved_expressions = parse_reserved_expressions(
        {
            "response": response,
            "answer": answer,
        },
        parameters
    )

    if parameters.get("physical_quantity", False) is True:
        eval_response = quantity_comparison(response, answer, parameters, eval_response)
    else:
        eval_response = symbolic_comparison(response, answer, parameters, eval_response)

    return eval_response.serialise(include_test_data)
