from inspect import getmembers, isfunction
import unit_system_conversions

f = open("static_unit_conversion_arrays.py","w",encoding="utf-8")
content = "# This is a generated file, do not edit. Changes to the unit conversion system should be done in unit_system_conversion.py\n"
functions = getmembers(unit_system_conversions,isfunction)
for function in functions:
    content += function[0]+"="+repr(function[1]())+"\n"
f.write(content)
f.close()