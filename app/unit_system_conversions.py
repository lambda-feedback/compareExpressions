# Remarks:
#   only K, no other temperature scales included
#   angles measures, bel an neper are all treated as identical dimensionless units

def list_of_SI_prefixes():
    """
    Prefixes taken from Table 5 https://physics.nist.gov/cuu/Units/prefixes.html
    """
    list = [
        ('yotta', 'Y',  '(10**24)'),
        ('zetta', 'Z',  '(10**21)'),
        ('exa',   'E',  '(10**18)'),
        ('peta',  'P',  '(10**15)'),
        ('tera',  'T',  '(10**12)'),
        ('giga',  'G',  '(10**9) '),
        ('mega',  'M',  '(10**6) '),
        ('kilo',  'k',  '(10**3) '),
        ('hecto', 'h',  '(10**2) '),
        ('deca',  'da', '(10**1) '),
        ('deci',  'd',  '(10**(-1)) '),
        ('centi', 'c',  '(10**(-2)) '),
        ('milli', 'm',  '(10**(-3)) '),
        ('micro', 'mu', '(10**(-6)) '),
        ('nano',  'n',  '(10**(-9)) '),
        ('pico',  'p',  '(10**(-12))'),
        ('femto', 'f',  '(10**(-15))'),
        ('atto',  'a',  '(10**(-18))'),
        ('zepto', 'z',  '(10**(-21))'),
        ('yocto', 'y',  '(10**(-24))')
        ]
    list.sort(key=lambda x: -len(x[0]))
    return list

def list_of_SI_base_unit_dimensions():
    """
    SI base units taken from Table 1 https://physics.nist.gov/cuu/Units/units.html
    Note that gram is used as a base unit instead of kilogram.
    """
    preop = lambda x:[(x,[" ","*","/"])]
    list = [
        ('metre',   'm',   'length',              preop('metres')+['meter']+preop('meters')),
        ('gram',    'g',   'mass',                preop('grams')),
        ('second',  's',   'time',                preop('seconds')),
        ('ampere',  'A',   'electric_current',    preop('amperes')+['Ampere']+preop('Amperes')),
        ('kelvin',  'K',   'temperature',         preop('kelvins')+['Kelvin']+preop('Kelvins')),
        ('mole',    'mol', 'amount_of_substance', preop('moles')),
        ('candela', 'cd',  'luminous_intensity',  preop('candelas')+['Candela']+preop('Candelas')),
        ]
    list.sort(key=lambda x: -len(x[0]))
    return list

def list_of_derived_SI_units_in_SI_base_units():
    """
    Derived SI units taken from Table 3 https://physics.nist.gov/cuu/Units/units.html
    Note that radians and degree have been moved to list_of_very_common_units_in_SI to reduce collisions when substituting.
    Note that degrees Celsius is omitted.
    """
    preop = lambda x:[(x,[" ","*","/"])]
    list = [
        ('hertz',     'Hz',  '(second**(-1))',                                      []),
        ('newton',    'N',   '(metre*kilo*gram*second**(-2))',                      preop('newtons')+['Newton']+preop('Newtons')),
        ('pascal',    'Pa',  '(metre**(-1)*kilogram*second**(-2))',                 preop('pascals')+['Pascal']+preop('Pascals')),
        ('joule',     'J',   '(metre**2*kilo*gram*second**(-2))',                   preop('joules')+['Joule']+preop('Joules')),
        ('watt',      'W',   '(metre**2*kilo*gram*second**(-3))',                   preop('watts')+['Watt']+preop('Watts')),
        ('coulomb',   'C',   '(second*ampere)',                                     preop('coulombs')+['Coulomb']+preop('Coulombs')),
        ('volt',      'V',   '(metre**2*kilo*gram*second**(-3)*ampere**(-1))',      preop('volts')+['Volt']+preop('Volts')),
        ('farad',     'F',   '(metre**(-2)*(kilo*gram)**(-1)*second**4*ampere**2)', preop('farads')+['Farad']+preop('Farads')),
        ('ohm',       'O',   '(metre**2*kilo*gram*second**(-3)*ampere**(-2))',      preop('ohms')+['Ohm']+preop('Ohms')),
        ('siemens',   'S',   '(metre**(-2)*kilo*gram**(-1)*second**3*ampere**2)',   preop('Siemens')),
        ('weber',     'Wb',  '(metre**2*kilo*gram*second**(-2)*ampere**(-1))',      preop('webers')+['Weber']+preop('Webers')),
        ('tesla',     'T',   '(kilo*gram*second**(-2)*ampere**(-1))',               preop('teslas')+['Tesla']+preop('Teslas')),
        ('henry',     'H',   '(metre**2*kilo*gram*second**(-2)*ampere**(-2))',      preop('henrys')+['Henry']+preop('Henrys')),
        ('lumen',     'lm',  '(candela)',                                           preop('lumens')),
        ('lux',       'lx',  '(metre**(-2)*candela)',                               []),
        ('becquerel', 'Bq',  '(second**(-1))',                                      preop('becquerels')+['Becquerel']+preop('Becquerels')),
        ('gray',      'Gy',  '(metre**2*second**(-2))',                             preop('grays')+['Gray']+preop('Grays')),
        ('sievert',   'Sv',  '(metre**2*second**(-2))',                             preop('sieverts')+['Sievert']+preop('Sieverts')),
        ('katal',     'kat', '(second**(-1)*mole)',                                 preop('katals')+['Katal']+preop('Katals'))
        ]
    list.sort(key=lambda x: -len(x[0]))
    return list

def list_of_very_common_units_in_SI():
    """
    Commonly used non-SI units taken from Table 6 and 7 https://physics.nist.gov/cuu/Units/outside.html
    Note that radian and steradian from Table 3 have been moved here to reduce collisions when substituting.
    This is the subset of common symbols whose short form symbols are allowed
    """
    preop = lambda x:[(x,[" ","*","/"])]
    list = [
        ('radian',    'r',   '(1)',                                   preop('radians')), # Note: here 'r' is used instead of the more common 'rad' to avoid collision
        ('steradian', 'sr',  '(1)',                                   preop('steradians')),
        ('minute',            'min', '(60*second)',                   preop('minutes')),
        ('hour',              'h',   '(3600*second)',                 preop('hours')),
        ('degree',            'deg', '(pi/180)',                      preop('degrees')),
        ('liter',             'L',   '(10**(-3)*metre**3)',           preop('liters')),
        ('metricton',         't',   '(10**3*kilo*gram)',             preop('tonne')+preop('tonnes')),
        ('neper',             'Np',  '(1)',                           preop('nepers')+['Neper']+preop('Nepers')),
        ('bel',               'B',   '((1/2)*log(10))',               preop('bels')+['Bel']+preop('Bels')),
        ('electronvolt',      'eV',  '(1.60218*10**(-19)*joule)',     preop('electronvolts')),
        ('atomicmassunit',    'u',   '(1.66054*10**(-27)*kilo*gram)', preop('atomicmassunits')),
        ('angstrom',          'å',   '(10**(-10)*metre)',             preop('angstroms')+['Angstrom']+preop('Angstroms')+['Ångström']),
        ]
    list.sort(key=lambda x: -len(x[0]))
    return list

def list_of_common_units_in_SI():
    """
    Commonly used non-SI units taken from Table 6 and 7 https://physics.nist.gov/cuu/Units/outside.html
    Note that short form symbols are defined here, but not used since they cause to many ambiguities
    """
    preop = lambda x:[(x,[" ","*","/"])]
    list = [
        ('day',               'd',   '(86400*second)',                     preop('days')),
        ('angleminute',       "'",   '(pi/10800)',                         []),
        ('anglesecond',       '"',   '(pi/648000)',                        []),
        ('astronomicalunit',  'au',  '(149597870700*metre)',               preop('astronomicalunits')),
        ('nauticalmile',      'nmi', '(1852*metre)',                       preop('nauticalmiles')), #Note: no short form in source, short form from Wikipedia
        ('knot',              'kn',  '((1852/3600)*metre/second)',         preop('knots')), #Note: no short form in source, short form from Wikipedia
        ('are',               'a',   '(10**2*metre**2)',                   preop('ares')),
        ('hectare',           'ha',  '(10**4*metre**2)',                   preop('hectares')),
        ('bar',               'bar', '(10**5*pascal)',                     preop('bars')),
        ('barn',              'b',   '(10**(-28)*metre**2)',               preop('barns')),
        ('curie',             'Ci',  '(3.7*10**10*becquerel)',             preop('curies')),
        ('roentgen',          'R',   '(2.58*10**(-4)*kelvin/(kilo*gram))', preop('roentgens')+['Roentgen']+preop('Roentgens')+['Röntgen']),
        ('rad',               'rad', '(10**(-2)*gray)',                    preop('rads')),
        ('rem',               'rem', '(10**(-2)*sievert)',                 preop('rems')),
        ]+list_of_very_common_units_in_SI()
    list.sort(key=lambda x: -len(x[0]))
    return list

def names_of_prefixes_units_and_dimensions():
    return tuple(x[0] for x in list_of_SI_prefixes())\
          +tuple(x[0] for x in list_of_SI_base_unit_dimensions())\
          +tuple(x[2] for x in list_of_SI_base_unit_dimensions())\
          +tuple(x[0] for x in list_of_derived_SI_units_in_SI_base_units())\
          +tuple(x[0] for x in list_of_common_units_in_SI())

def names_of_all_units_and_dimensions():
    return tuple(x[0] for x in list_of_SI_prefixes())\
          +tuple(x[0] for x in list_of_SI_base_unit_dimensions())\
          +tuple(x[2] for x in list_of_SI_base_unit_dimensions())\
          +tuple(x[0] for x in list_of_common_units_in_SI())

def convert_short_forms():
    units = list_of_SI_base_unit_dimensions()\
           +list_of_derived_SI_units_in_SI_base_units()\
           +list_of_very_common_units_in_SI()
    protect_long_forms = [(x[0],x[0]) for x in units]\
                        +[(x[0],x[0]) for x in list_of_common_units_in_SI()]\
                        +[(x[2],x[2]) for x in list_of_SI_base_unit_dimensions()]\
                        +[(x[0],x[0]) for x in list_of_SI_prefixes()]
    protect_long_forms.sort(key=lambda x: -len(x[0]))
    collision_fixes = []
    for prefix in list_of_SI_prefixes():
        for unit in units:
            collision_fixes.append((prefix[1]+unit[1],     prefix[0]+"*("+unit[0]+")"))
            collision_fixes.append((prefix[1]+"*"+unit[1], prefix[0]+"*("+unit[0]+")"))
            collision_fixes.append((prefix[1]+" "+unit[1], prefix[0]+"*("+unit[0]+")"))
    collision_fixes.sort(key=lambda x: -len(x[0]))
    convert_short_forms_list = [(x[1],x[0]) for x in units]
    convert_short_forms_list.sort(key=lambda x: -len(x[0]))
    return protect_long_forms+collision_fixes+convert_short_forms_list

def convert_to_SI_base_units():
    protect_base_units = [(x[0],x[0]) for x in list_of_SI_base_unit_dimensions()]
    return [protect_base_units+[(x[0],x[2]) for x in list_of_derived_SI_units_in_SI_base_units()],\
            protect_base_units+[(x[0],x[2]) for x in list_of_common_units_in_SI()],\
            protect_base_units+[(x[0],x[2]) for x in list_of_derived_SI_units_in_SI_base_units()],\
            protect_base_units+[(x[0],x[2]) for x in list_of_SI_prefixes()]]

def convert_to_SI_base_units_short_form():
    return [convert_short_forms()]+convert_to_SI_base_units()

def convert_SI_base_units_to_dimensions(): 
    return convert_to_SI_base_units()+[[(x[0],x[2]) for x in list_of_SI_base_unit_dimensions()]]

def convert_SI_base_units_to_dimensions_short_form(): 
    return convert_to_SI_base_units_short_form()+[[(x[0],x[2]) for x in list_of_SI_base_unit_dimensions()]]

def convert_alternative_names_to_standard():
    standard_alternatives = list_of_SI_base_unit_dimensions()+list_of_derived_SI_units_in_SI_base_units()+list_of_common_units_in_SI()
    convert_to_standard = []
    for elem in standard_alternatives:
        standard = elem[0]
        alternatives = elem[3]
        for alternative in alternatives:
            convert_to_standard.append((alternative,standard))
    convert_to_standard.sort(key=lambda x: -max(len(x[0]),len(x[0][0])))
    return convert_to_standard

def base_unit_dictionary():
    base_units = {x[0]: x[0] for x in list_of_SI_base_unit_dimensions()}
    base_units_short = {x[1]: x[0] for x in list_of_SI_base_unit_dimensions()}
    return {**base_units, **base_units_short}

def unit_dictionary():
    base_units = {x[0]: x[0] for x in list_of_SI_base_unit_dimensions()}
    base_units_short = {x[1]: x[0] for x in list_of_SI_base_unit_dimensions()}
    prefixes = {x[0]: x[0] for x in list_of_SI_prefixes()}
    prefixes_short = {x[1]: x[0] for x in list_of_SI_prefixes()}
    units = base_units
    units_short = base_units_short
    prefixed_units = {}
    for prefix in prefixes.keys():
        for unit in units.keys():
            prefixed_units.update({prefix+unit: prefix+unit})
    for prefix in prefixes_short.keys():
        for unit in units_short.keys():
            prefixed_units.update({prefix+unit: prefixes_short[prefix]+units_short[unit]})
    return {**base_units, **base_units_short, **prefixed_units}

def conversion_to_base_si_units_dictionary():
    base_units = {x[0]: "(1*"+x[0]+")" for x in list_of_SI_base_unit_dimensions()}
    base_units_short = {x[1]: "(1*"+x[0]+")" for x in list_of_SI_base_unit_dimensions()}
    prefixes = {x[0]: x[2]+"*" for x in list_of_SI_prefixes()}
    prefixes_short = {x[1]: x[2]+"*" for x in list_of_SI_prefixes()}
    units = base_units
    units_short = base_units_short
    prefixed_units = {}
    for prefix in prefixes.keys():
        for unit in units.keys():
            prefixed_units.update({prefix+unit: "("+prefixes[prefix]+units[unit]+")"})
    for prefix in prefixes_short.keys():
        for unit in units_short.keys():
            prefixed_units.update({prefix+unit: "("+prefixes_short[prefix]+units_short[unit]+")"})
    return {**base_units, **base_units_short, **prefixed_units}