feedback_string_generators = dict()
feedback_string_generators["INTERNAL"] = lambda tag: lambda inputs: {
    "REVERTED_UNIT": f"Possible ambiguity: <strong>`{inputs.get('marked', '')}`</strong> was not interpreted as a unit in<br>`{inputs['before']}`<strong>`{inputs['marked']}`</strong>`{inputs['after']}`",
}[tag]
feedback_string_generators["MATCHES"] = lambda tag: lambda inputs: {
    "QUANTITY_MATCH": f"{inputs.get('lhs', '')} matches {inputs.get('rhs', '')}.",
    "QUANTITY_MISMATCH": f"{inputs.get('lhs', '')} does not match {inputs.get('rhs', '')}.",
    "MISSING_VALUE": "The response is missing a value.",
    "UNEXPECTED_VALUE": "The response is expected only have unit(s), no value.",
    "MISSING_UNIT": "The response is missing unit(s).",
    "UNEXPECTED_UNIT": "The response is expected to be a value without unit(s).",
    "DIMENSION_MATCH": f" ${inputs.get('lhs', '')}$ has the expected dimensions",
    "DIMENSION_MISMATCH": f"${inputs.get('lhs', '')}$ does not have the expected dimensions",
    "UNIT_COMPARISON_IDENTICAL": "",  # In this case the response is written exactly as expected
    "UNIT_COMPARISON_SIMILAR": "",  # In this case the response is written similarly to what is expected
    "PREFIX_IS_LARGE": "The quantity can be written with fewer digits by using a smaller prefix.",
    "PREFIX_IS_SMALL": "The quantity can be written with fewer digits by using a larger prefix.",
}[tag]