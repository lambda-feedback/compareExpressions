import pytest
from slr_strict_si_syntax import SLR_strict_SI_parsing

@pytest.mark.parametrize("string,value,unit,content,unit_latex",[
    ("q",\
     "q",None,\
     "q",\
     None),
    ("10",\
     "10",None,\
     "10",\
     None),
    ("-10.5*4",\
     "-10.5*4",None,\
     "-10.5*4",\
     None),
    ("pi*5",\
     "pi*5",None,\
     "pi*5",\
     None),
    ("5*pi",\
     "5*pi",None,\
     "5*pi",\
     None),
    ("sin(-10.5*4)",\
     "sin(-10.5*4)",None,\
     "sin(-10.5*4)",\
     None),
    ("kilogram/(metre second^2)",\
     None,"kilogram/(metre second^2)",\
     "kilogram/(metre second^2)",\
     r"\frac{\mathrm{kilogram}}{(\mathrm{metre}~\mathrm{second}^{2})}"),
    ("10 kilogram/(metre second^2)",\
     "10","kilogram/(metre second^2)",\
     "10 kilogram/(metre second^2)",\
     r"\frac{\mathrm{kilogram}}{(\mathrm{metre}~\mathrm{second}^{2})}"),
    ("10 kilogram*metre/second**2",\
     "10","kilogram*metre/second**2",\
     "10 kilogram*metre/second**2",\
     r"\mathrm{kilogram}\cdot\frac{\mathrm{metre}}{\mathrm{second}^{2}}"),
    ("-10.5 kg m/s^2",\
     "-10.5","kg m/s^2",\
     "-10.5 kilogram metre/second^2",\
     r"\mathrm{kilogram}~\frac{\mathrm{metre}}{\mathrm{second}^{2}}"),
    ("10 kilogram*metre*second**(-2)",\
     "10","kilogram*metre*second**(-2)",\
     "10 kilogram*metre*second**(-2)",
     r"\mathrm{kilogram}\cdot\mathrm{metre}\cdot\mathrm{second}^{(-2)}"),
    ("10*pi kilogram*metre/second^2",\
     "10*pi","kilogram*metre/second^2",\
     "10*pi kilogram*metre/second^2",
     r"\mathrm{kilogram}\cdot\frac{\mathrm{metre}}{\mathrm{second}^{2}}"),
    ("(5.27*pi/sqrt(11) + 5*7)^(4.3)",\
     "(5.27*pi/sqrt(11) + 5*7)^(4.3)",None,\
     "(5.27*pi/sqrt(11) + 5*7)^(4.3)",\
     None),
    ("(kilogram megametre^2)/(fs^4 daA)",\
     None,"(kilogram megametre^2)/(fs^4 daA)",\
     "(kilogram megametre^2)/(femtosecond^4 dekaampere)",\
     r"\frac{(\mathrm{kilogram}~\mathrm{megametre}^{2})}{(\mathrm{femtosecond}^{4}~\mathrm{dekaampere})}"),
    ("(5.27*pi/sqrt(11) + 5*7)^(4.3) (kilogram megametre^2)/(fs^4 daA)",\
     "(5.27*pi/sqrt(11) + 5*7)^(4.3)","(kilogram megametre^2)/(fs^4 daA)",\
     "(5.27*pi/sqrt(11) + 5*7)^(4.3) (kilogram megametre^2)/(femtosecond^4 dekaampere)",\
     r"\frac{(\mathrm{kilogram}~\mathrm{megametre}^{2})}{(\mathrm{femtosecond}^{4}~\mathrm{dekaampere})}"),
    ("(5.27*pi/sqrt(11) + 5*7)^(2+2.3) (kilogram megametre^2)/(fs^4 daA)",\
     "(5.27*pi/sqrt(11) + 5*7)^(2+2.3)","(kilogram megametre^2)/(fs^4 daA)",\
     "(5.27*pi/sqrt(11) + 5*7)^(2+2.3) (kilogram megametre^2)/(femtosecond^4 dekaampere)",\
     r"\frac{(\mathrm{kilogram}~\mathrm{megametre}^{2})}{(\mathrm{femtosecond}^{4}~\mathrm{dekaampere})}"),
    ("(5*27/11 + 5*7)^(2*3) (kilogram megametre^2)/(fs^4 daA)",\
     "(5*27/11 + 5*7)^(2*3)","(kilogram megametre^2)/(fs^4 daA)",\
     "(5*27/11 + 5*7)^(2*3) (kilogram megametre^2)/(femtosecond^4 dekaampere)",\
     r"\frac{(\mathrm{kilogram}~\mathrm{megametre}^{2})}{(\mathrm{femtosecond}^{4}~\mathrm{dekaampere})}"),
    ("(pi+10) kg*m/s^2",\
     "(pi+10)","kg*m/s^2",\
     "(pi+10) kilogram*metre/second^2",\
     r"\mathrm{kilogram}\cdot\frac{\mathrm{metre}}{\mathrm{second}^{2}}"),
    ("10 kilogram*metre/second^2",\
     "10","kilogram*metre/second^2",\
     "10 kilogram*metre/second^2",\
     r"\mathrm{kilogram}\cdot\frac{\mathrm{metre}}{\mathrm{second}^{2}}"),
    ("10 kg*m/s^2",\
     "10","kg*m/s^2",\
     "10 kilogram*metre/second^2",\
     r"\mathrm{kilogram}\cdot\frac{\mathrm{metre}}{\mathrm{second}^{2}}"),
    (" 10 kg m/s^2 ",\
     "10","kg m/s^2",\
     "10 kilogram metre/second^2",\
     r"\mathrm{kilogram}~\frac{\mathrm{metre}}{\mathrm{second}^{2}}"),
    ("10 gram/metresecond",\
     "10 gram/metresecond",None,\
     "10 gram/metresecond",\
     None),
    ("10 second/gram + 5 gram*second^2 + 7 ms + 5 gram/second^3",\
     "10 second/gram + 5 gram*second^2 + 7 ms + 5","gram/second^3",\
     "10 second/gram + 5 gram*second^2 + 7 ms + 5 gram/second^3",\
     r"\frac{\mathrm{gram}}{\mathrm{second}^{3}}"),
    ("10 second/gram * 7 ms * 5 gram/second",\
     "10 second/gram * 7 ms * 5","gram/second",\
     "10 second/gram * 7 ms * 5 gram/second",\
     r"\frac{\mathrm{gram}}{\mathrm{second}}"),
    ("pi+metre second+pi",\
     "pi+metre second+pi",None,\
     "pi+metre second+pi",\
     None),
    ("1/s^2",\
     None,"1/s^2",\
     "1/second^2",\
     r"\frac{1}{\mathrm{second}^{2}}"),
    ("5/s^2",\
     "5/s^2",None,\
     "5/s^2",\
     None),
    ("10 1/s^2",\
     "10","1/s^2",\
     "10 1/second^2",\
     r"\frac{1}{\mathrm{second}^{2}}"),
    ])
def test_responses(string,value,unit,content,unit_latex):
    quantity, parsed_unit_latex = SLR_strict_SI_parsing(string)
    parsed_value = quantity.value.original_string() if quantity.value != None else None
    parsed_unit = quantity.unit.original_string() if quantity.unit != None else None
    parsed_content = quantity.ast_root.content_string()
    assert parsed_value == value
    assert parsed_unit == unit
    assert parsed_content == content
    assert parsed_unit_latex == unit_latex

if __name__ == "__main__":
    import os 
    pytest.main(["--tb=line",os.path.basename(__file__)])