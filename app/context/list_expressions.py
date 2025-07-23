

from copy import deepcopy
from ..utility.evaluation_result_utilities import EvaluationResult

#reusing app/context/symbolic.py code
from .symbolic import context as symbolic_context

#list of previews for list of expressions
def expression_preview(response, parameters):
    # preview each sub‐expression with the regular symbolic preview
    previews = [symbolic_context["expression_preview"](r, parameters)["preview"]
                for r in response]
    return {"preview": previews}

#preprocess from symbolic done on each element
def expression_preprocess(name, expr, parameters):

    return all(symbolic_context["expression_preprocess"](name, e, parameters)[0] for e in expr), expr, None

#chatgpt recommended  - so we can have a stub in list_context
#should not be called anyway since list inputs should be handled before parsing in app/evaluation.py
def expression_parse(name, expr, parameters, evaluation_result):

    raise RuntimeError("Should not parse a list at list‐context level")

#these variables are needed to fill in list_context
default_parameters = deepcopy(symbolic_context["default_parameters"])
default_criteria   = symbolic_context["default_criteria"]

#the next 3 functiions are to complete list_context using the same functions from app/context/symbolic.py
def feedback_procedure_generator(parameters_dict):
  
    return symbolic_context["feedback_procedure_generator"](parameters_dict)


def feedback_string_generator(tags, graph, parameters_dict):
    return symbolic_context["feedback_string_generator"](tags, graph, parameters_dict)


def parsing_parameters_generator(params, **kw):
    return symbolic_context["parsing_parameters_generator"](params, **kw)


list_context = {
    "expression_preview":         expression_preview,
    "expression_preprocess":      expression_preprocess,
    "expression_parse":           expression_parse,
    "default_parameters":         default_parameters,
    "default_criteria":           default_criteria,
    "feedback_procedure_generator": feedback_procedure_generator,
    "feedback_string_generator":  feedback_string_generator,
    "parsing_parameters_generator": parsing_parameters_generator,
}
