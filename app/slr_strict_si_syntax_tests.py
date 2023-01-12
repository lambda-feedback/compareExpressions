import pytest
import sys
sys.path.append(".")

from slr_strict_si_syntax import SLR_strict_SI_parsing

slr_strict_si_syntax_test_cases = [
    ("q",\
    "q",None,\
    "q",\
    None,\
    ["NO_UNIT"]),
    ("10",\
    "10",None,\
    "10",\
    None,\
    ["NO_UNIT"]),
    ("-10.5*4",\
    "-10.5*4",None,\
    "-10.5*4",\
    None,\
    ["NO_UNIT"]),
    ("pi*5",\
    "pi*5",None,\
    "pi*5",\
    None,\
    ["NO_UNIT"]),
    ("5*pi",\
    "5*pi",None,\
    "5*pi",\
    None,\
    ["NO_UNIT"]),
    ("sin(-10.5*4)",\
    "sin(-10.5*4)",None,\
    "sin(-10.5*4)",\
    None,\
    ["NO_UNIT"]),
    ("kilogram/(metre second^2)",\
    None,"kilogram/(metre second^2)",\
    "kilogram/(metre second^2)",\
    r"\frac{\mathrm{kilogram}}{(\mathrm{metre}~\mathrm{second}^{2})}",\
    ["NO_VALUE"]),
    ("10 kilogram/(metre second^2)",\
    "10","kilogram/(metre second^2)",\
    "10 kilogram/(metre second^2)",\
    r"\frac{\mathrm{kilogram}}{(\mathrm{metre}~\mathrm{second}^{2})}",\
    ["FULL_QUANTITY","NUMBER_VALUE"]),
    ("10 kilogram*metre/second**2",\
    "10","kilogram*metre/second**2",\
    "10 kilogram*metre/second**2",\
    r"\mathrm{kilogram}\cdot\frac{\mathrm{metre}}{\mathrm{second}^{2}}",\
    ["FULL_QUANTITY","NUMBER_VALUE"]),
    ("-10.5 kg m/s^2",\
    "-10.5","kg m/s^2",\
    "-10.5 kilogram metre/second^2",\
    r"\mathrm{kilogram}~\frac{\mathrm{metre}}{\mathrm{second}^{2}}",\
    ["FULL_QUANTITY","NUMBER_VALUE"]),
    ("10 kilogram*metre*second**(-2)",\
    "10","kilogram*metre*second**(-2)",\
    "10 kilogram*metre*second**(-2)",
    r"\mathrm{kilogram}\cdot\mathrm{metre}\cdot\mathrm{second}^{(-2)}",\
    ["FULL_QUANTITY","NUMBER_VALUE"]),
    ("10*pi kilogram*metre/second^2",\
    "10*pi","kilogram*metre/second^2",\
    "10*pi kilogram*metre/second^2",
    r"\mathrm{kilogram}\cdot\frac{\mathrm{metre}}{\mathrm{second}^{2}}",\
    ["FULL_QUANTITY","EXPR_VALUE"]),
    ("(5.27*pi/sqrt(11) + 5*7)^(4.3)",\
    "(5.27*pi/sqrt(11) + 5*7)^(4.3)",None,\
    "(5.27*pi/sqrt(11) + 5*7)^(4.3)",\
    None,\
    ["NO_UNIT","EXPR_VALUE"]),
    ("(kilogram megametre^2)/(fs^4 daA)",\
    None,"(kilogram megametre^2)/(fs^4 daA)",\
    "(kilogram megametre^2)/(femtosecond^4 dekaampere)",\
    r"\frac{(\mathrm{kilogram}~\mathrm{megametre}^{2})}{(\mathrm{femtosecond}^{4}~\mathrm{dekaampere})}",\
    ["NO_VALUE"]),
    ("(5.27*pi/sqrt(11) + 5*7)^(4.3) (kilogram megametre^2)/(fs^4 daA)",\
    "(5.27*pi/sqrt(11) + 5*7)^(4.3)","(kilogram megametre^2)/(fs^4 daA)",\
    "(5.27*pi/sqrt(11) + 5*7)^(4.3) (kilogram megametre^2)/(femtosecond^4 dekaampere)",\
    r"\frac{(\mathrm{kilogram}~\mathrm{megametre}^{2})}{(\mathrm{femtosecond}^{4}~\mathrm{dekaampere})}",\
    ["FULL_QUANTITY","EXPR_VALUE"]),
    ("(5.27*pi/sqrt(11) + 5*7)^(2+2.3) (kilogram megametre^2)/(fs^4 daA)",\
    "(5.27*pi/sqrt(11) + 5*7)^(2+2.3)","(kilogram megametre^2)/(fs^4 daA)",\
    "(5.27*pi/sqrt(11) + 5*7)^(2+2.3) (kilogram megametre^2)/(femtosecond^4 dekaampere)",\
    r"\frac{(\mathrm{kilogram}~\mathrm{megametre}^{2})}{(\mathrm{femtosecond}^{4}~\mathrm{dekaampere})}",\
    ["FULL_QUANTITY","EXPR_VALUE"]),
    ("(5*27/11 + 5*7)^(2*3) (kilogram megametre^2)/(fs^4 daA)",\
    "(5*27/11 + 5*7)^(2*3)","(kilogram megametre^2)/(fs^4 daA)",\
    "(5*27/11 + 5*7)^(2*3) (kilogram megametre^2)/(femtosecond^4 dekaampere)",\
    r"\frac{(\mathrm{kilogram}~\mathrm{megametre}^{2})}{(\mathrm{femtosecond}^{4}~\mathrm{dekaampere})}",\
    ["FULL_QUANTITY","EXPR_VALUE"]),
    ("(pi+10) kg*m/s^2",\
    "(pi+10)","kg*m/s^2",\
    "(pi+10) kilogram*metre/second^2",\
    r"\mathrm{kilogram}\cdot\frac{\mathrm{metre}}{\mathrm{second}^{2}}",\
    ["FULL_QUANTITY","EXPR_VALUE"]),
    ("10 kilogram*metre/second^2",\
    "10","kilogram*metre/second^2",\
    "10 kilogram*metre/second^2",\
    r"\mathrm{kilogram}\cdot\frac{\mathrm{metre}}{\mathrm{second}^{2}}",\
    ["FULL_QUANTITY","NUMBER_VALUE"]),
    ("10 kg*m/s^2",\
    "10","kg*m/s^2",\
    "10 kilogram*metre/second^2",\
    r"\mathrm{kilogram}\cdot\frac{\mathrm{metre}}{\mathrm{second}^{2}}",\
    ["FULL_QUANTITY","NUMBER_VALUE"]),
    (" 10 kg m/s^2 ",\
    "10","kg m/s^2",\
    "10 kilogram metre/second^2",\
    r"\mathrm{kilogram}~\frac{\mathrm{metre}}{\mathrm{second}^{2}}",\
    ["FULL_QUANTITY","NUMBER_VALUE"]),
    ("10 gram/metresecond",\
    "10 gram/metresecond",None,\
    "10 gram/metresecond",\
    None,\
    ["NO_UNIT","EXPR_VALUE"]),
    ("10 s/g + 5 gram*second^2 + 7 ms + 5 gram/second^3",\
    "10 s/g + 5 gram*second^2 + 7 ms + 5","gram/second^3",\
    "10 s/g + 5 gram*second^2 + 7 ms + 5 gram/second^3",\
    r"\frac{\mathrm{gram}}{\mathrm{second}^{3}}",\
    ["FULL_QUANTITY","EXPR_VALUE"]),
    ("10 second/gram * 7 ms * 5 gram/second",\
    "10 second/gram * 7 ms * 5","gram/second",\
    "10 second/gram * 7 ms * 5 gram/second",\
    r"\frac{\mathrm{gram}}{\mathrm{second}}",\
    ["FULL_QUANTITY","EXPR_VALUE"]),
    ("pi+metre second+pi",\
    "pi+metre second+pi",None,\
    "pi+metre second+pi",\
    None,\
    ["EXPR_VALUE","NO_UNIT"]),
    ("1/s^2",\
    None,"1/s^2",\
    "1/second^2",\
    r"\frac{1}{\mathrm{second}^{2}}",\
    ["NO_VALUE","HAS_UNIT"]),
    ("5/s^2",\
    "5/s^2",None,\
    "5/s^2",\
    None,\
    ["NO_UNIT","EXPR_VALUE"]),
    ("10 1/s^2",\
    "10","1/s^2",\
    "10 1/second^2",\
    r"\frac{1}{\mathrm{second}^{2}}",\
    ["FULL_QUANTITY","NUMBER_VALUE"]),
]

class TestClass:
    @pytest.mark.parametrize("string,value,unit,content,unit_latex,criteria",slr_strict_si_syntax_test_cases)
    def test_responses(self,string,value,unit,content,unit_latex,criteria):
        quantity, parsed_unit_latex = SLR_strict_SI_parsing(string)
        parsed_value = quantity.value.original_string() if quantity.value != None else None
        parsed_unit = quantity.unit.original_string() if quantity.unit != None else None
        parsed_content = quantity.ast_root.content_string()
        assert parsed_value == value
        assert parsed_unit == unit
        assert parsed_content == content
        assert parsed_unit_latex == unit_latex
        for criterion in criteria:
            assert criterion in quantity.passed_dict

if __name__ == "__main__":
    import os 
    pytest.main(["-x", "--tb=line",os.path.basename(__file__)])