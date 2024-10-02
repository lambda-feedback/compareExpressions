from .evaluation_response_utilities import EvaluationResponse
from .symbolic_comparison_evaluation import evaluation_function as symbolic_comparison
from .slr_quantity import quantity_comparison
from .preview import preview_function

from .benchmarking import benchmarks
from timeit import default_timer as timer

def evaluation_function(response, answer, params, include_test_data=False) -> dict:
    """
    Function that allows for various types of comparison of various kinds of expressions.
    Supported input parameters:
    strict_SI_syntax:
        - if set to True, use basic dimensional analysis functionality.
    """

    if response.lower().startswith("benchmark"):
        arg = response.split()
        n = 1
        val = True
        if len(arg) > 1:
            n = int(arg[1])
        if len(arg) > 2:
            if arg[2].lower().startswith("f"):
                val = False
        results = []
        total = 0
        for k, test in enumerate(benchmarks,1):
            avg = 0
            for i in range(0,n):
                start = timer()
                result = evaluation_function(
                    test["response"],
                    test["answer"],
                    test["params"]
                )
                end = timer()
                avg += end-start
            total += avg
            avg = avg/n
            results.append(f"Time for test {k}: {avg}")
        return {"is_correct": val, "feedback": r"<br>".join(results)+r"<br>"+"Total: "+str(total)}

    eval_response = EvaluationResponse()
    eval_response.is_correct = False

    input_symbols_reserved_words = []

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
        if len(reserved_keywords_collisions) == 1:
            raise Exception("`"+"`, `".join(reserved_keywords_collisions)+"` is a reserved keyword and cannot be used as an input symbol alternative.")
        else:
            raise Exception("`"+"`, `".join(reserved_keywords_collisions)+"` are reserved keywords and cannot be used as input symbol alternatives.")

    parameters = {
        "comparison": "expression",
        "strict_syntax": True,
        "reserved_keywords": reserved_keywords,
    }
    parameters.update(params)

    if params.get("is_latex", False):
        response = preview_function(response, params)["preview"]["sympy"]

    if parameters.get("physical_quantity", False) is True:
        eval_response = quantity_comparison(response, answer, parameters, eval_response)
    else:
        eval_response = symbolic_comparison(response, answer, parameters, eval_response)

    if eval_response.is_correct is False and parameters.get("feedback_for_incorrect_response", None) is not None:
        result_dict = eval_response.serialise(include_test_data)
        result_dict["feedback"] = parameters["feedback_for_incorrect_response"]
        return result_dict

    return eval_response.serialise(include_test_data)
