from enum import Enum
QuantityTags = Enum("QuantityTags", {v: i for i, v in enumerate("UVNR", 1)})

criteria = dict()
basic_criteria = [
    {
        f"has(unit({q.lower()}))":
        {
            True:  (f"{q.upper()}_HAS_UNIT", lambda inputs: f"{q} has unit: "+inputs[0].unit.content_string()),
            False: (f"{q.upper()}_NO_UNIT",  lambda inputs: f"{q} has no unit.")
        },
        f"has(value({q.lower()}))":
        {
            True:  (f"{q.upper()}_HAS_VALUE", lambda inputs: f"{q} has value: "+inputs[0].value.content_string()),
            False: (f"{q.upper()}_NO_VALUE",  lambda inputs: f"{q} has no value.")
        },
        f"has(value({q.lower()})) and not(has(unit({q.lower()})))":
        {
            True:  (f"{q.upper()}_ONLY_VALUE",     lambda inputs: f"{q} has no unit, only value: "+inputs[0].value.content_string()),
            False: (f"{q.upper()}_NOT_ONLY_VALUE", lambda inputs: "")  # Since there is no easy way to tell which part of the condition has failed, no feedback will be given in this case
        },
        f"not(has(value({q.lower()}))) and has(unit({q.lower()}))":
        {
            True:  (f"{q.upper()}_ONLY_UNIT",     lambda inputs: f"{q} has no value, only unit: "+inputs[0].unit.content_string()),
            False: (f"{q.upper()}_NOT_ONLY_UNIT", lambda inputs: "")  # Since there is no easy way to tell which part of the condition has failed, no feedback will be given in this case
        },
        f"has(value({q.lower()})) and has(unit({q.lower()}))":
        {
            True:  (f"{q.upper()}_FULL_QUANTITY",     lambda inputs: f"{q} has both value and unit.<br>Value: "+inputs[0].value.content_string()+"<br>Unit: "+inputs[0].unit.content_string()),
            False: (f"{q.upper()}_NOT_FULL_QUANTITY", lambda inputs: "")  # Since there is no easy way to tell which part of the condition has failed, no feedback will be given in this case
        },
        f"is_number(value({q.lower()}))":
        {
            True:  (f"{q.upper()}_NUMBER_VALUE",     lambda inputs: f"{q} value is a number: "+inputs[0].value.content_string()),
            False: (f"{q.upper()}_NOT_NUMBER_VALUE", lambda inputs: f"{q} value is not a number.")
        },
        f"is_expression(value({q.lower()}))":
        {
            True:  (f"{q.upper()}_EXPR_VALUE",     lambda inputs: f"{q} value is an expression: "+inputs[0].value.content_string()),
            False: (f"{q.upper()}_NOT_EXPR_VALUE", lambda inputs: f"{q} value is not an expression.")
        }
    } for q in ["Response", "Answer"]
]
criteria.update({**basic_criteria[0], **basic_criteria[1]})
#criteria.update(
#    {
#        "unit(answer) matches unit(response)":
#        {
#            True:  ("UNIT_MATCH",     lambda inputs: inputs[0].unit.content_string()+" matches "+inputs[1].unit.content_string()),
#            False: ("NOT_UNIT_MATCH", lambda inputs: inputs[0].unit.content_string()+" does not match "+inputs[1].unit.content_string())
#        },
#        "value(answer) matches value(response)":
#        {
#            True:  ("VALUE_MATCH",     lambda inputs: inputs[0].value.content_string()+" does not match "+inputs[1].value.content_string()),
#            False: ("NOT_VALUE_MATCH", lambda inputs: inputs[0].value.content_string()+" does not match "+inputs[1].value.content_string())
#        }
#    }
#)

internal = {
    "REVERTED_UNIT": lambda before, content, after: "Possible ambiguity: <strong>`"+content+"`</strong> was not interpreted as a unit in<br>`"+before+"`<strong>`"+content+"`</strong>`"+after+"`"
}
