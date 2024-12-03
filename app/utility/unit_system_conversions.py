# Remarks:
#   only K, no other temperature scales included
#   angles measures, bel an neper are all treated as identical dimensionless units

"""
Prefixes taken from Table 5 https://physics.nist.gov/cuu/Units/prefixes.html and https://www.bipm.org/en/cgpm-2022/resolution-3
"""
set_of_SI_prefixes = {
    ('quetta', 'Q',  '(10**30)',    tuple()),
    ('ronna',  'R',  '(10**27)',    tuple()),
    ('yotta',  'Y',  '(10**24)',    tuple()),
    ('zetta',  'Z',  '(10**21)',    tuple()),
    ('exa',    'E',  '(10**18)',    tuple()),
    ('peta',   'P',  '(10**15)',    tuple()),
    ('tera',   'T',  '(10**12)',    tuple()),
    ('giga',   'G',  '(10**9)',     tuple()),
    ('mega',   'M',  '(10**6)',     tuple()),
    ('kilo',   'k',  '(10**3)',     tuple()),
    ('hecto',  'h',  '(10**2)',     tuple()),
    ('deca',   'da', '(10**1)',     ('deka',)),
    ('deci',   'd',  '(10**(-1))',  tuple()),
    ('centi',  'c',  '(10**(-2))',  tuple()),
    ('milli',  'm',  '(10**(-3))',  tuple()),
    ('micro',  'mu', '(10**(-6))',  tuple()),
    ('nano',   'n',  '(10**(-9))',  tuple()),
    ('pico',   'p',  '(10**(-12))', tuple()),
    ('femto',  'f',  '(10**(-15))', tuple()),
    ('atto',   'a',  '(10**(-18))', tuple()),
    ('zepto',  'z',  '(10**(-21))', tuple()),
    ('yocto',  'y',  '(10**(-24))', tuple()),
    ('ronto',  'r',  '(10**(-27))', tuple()),
    ('quecto', 'q',  '(10**(-30))', tuple())
}

"""
SI base units taken from Table 1 https://physics.nist.gov/cuu/Units/units.html
Note that gram is used as a base unit instead of kilogram.
"""
set_of_SI_base_unit_dimensions = {
    ('metre',   'm',   'length',              ('meter',),   ('metres', 'meters')),
    ('gram',    'g',   'mass',                tuple(),      ('grams',)),
    ('second',  's',   'time',                tuple(),      ('seconds',)),
    ('ampere',  'A',   'electric_current',    ('Ampere',),  ('amperes', 'Amperes')),
    ('kelvin',  'K',   'temperature',         ('Kelvin',),  ('kelvins', 'Kelvins')),
    ('mole',    'mol', 'amount_of_substance', tuple(),      ('moles',)),
    ('candela', 'cd',  'luminous_intensity',  ('Candela',), ('candelas', 'Candelas')),
}

"""
Derived SI units taken from Table 3 https://physics.nist.gov/cuu/Units/units.html
Note that radians and degree have been moved to list_of_very_common_units_in_SI to reduce collisions when substituting.
Note that degrees Celsius is omitted.
"""
set_of_derived_SI_units_in_SI_base_units = {
    ('hertz',     'Hz',  '(second**(-1))',                                     ('Hertz',),     tuple()),
    ('newton',    'N',   '(metre*kilogram*second**(-2))',                      ('Newton',),    ('newtons', 'Newtons')),
    ('pascal',    'Pa',  '(metre**(-1)*kilogram*second**(-2))',                ('Pascal',),    ('pascals', 'Pascals')),
    ('joule',     'J',   '(metre**2*kilogram*second**(-2))',                   ('Joule',),     ('joules', 'Joules')),
    ('watt',      'W',   '(metre**2*kilogram*second**(-3))',                   ('Watt',),      ('watts', 'Watts')),
    ('coulomb',   'C',   '(second*ampere)',                                    ('Coulomb',),   ('coulombs', 'Coulombs')),
    ('volt',      'V',   '(metre**2*kilogram*second**(-3)*ampere**(-1))',      ('Volt',),      ('volts', 'Volts')),
    ('farad',     'F',   '(metre**(-2)*(kilogram)**(-1)*second**4*ampere**2)', ('Farad',),     ('farads', 'Farads')),
    ('ohm',       'O',   '(metre**2*kilogram*second**(-3)*ampere**(-2))',      ('Ohm',),       ('ohms', 'Ohms')),
    ('siemens',   'S',   '(metre**(-2)*kilogram**(-1)*second**3*ampere**2)',   ('Siemens',),   tuple()),
    ('weber',     'Wb',  '(metre**2*kilogram*second**(-2)*ampere**(-1))',      ('Weber',),     ('webers', 'Webers')),
    ('tesla',     'T',   '(kilogram*second**(-2)*ampere**(-1))',               ('Tesla',),     ('teslas', 'Teslas')),
    ('henry',     'H',   '(metre**2*kilogram*second**(-2)*ampere**(-2))',      ('Henry',),     ('henrys', 'Henrys')),
    ('lumen',     'lm',  '(candela)',                                           tuple(),        ('lumens',)),
    ('lux',       'lx',  '(metre**(-2)*candela)',                               tuple(),        tuple()),
    ('becquerel', 'Bq',  '(second**(-1))',                                      ('Becquerel',), ('becquerels', 'Becquerels')),
    ('gray',      'Gy',  '(metre**2*second**(-2))',                             ('Gray',),      ('grays', 'Grays')),
    ('sievert',   'Sv',  '(metre**2*second**(-2))',                             ('Sievert',),   ('sieverts', 'Sieverts')),
    ('katal',     'kat', '(second**(-1)*mole)',                                 ('Katal',),     ('katals', 'Katals'))
}

"""
Commonly used non-SI units taken from Table 6 and 7 https://physics.nist.gov/cuu/Units/outside.html
Note that radian and steradian from Table 3 have been moved here to reduce collisions when substituting.
This is the subset of common symbols whose short form symbols are allowed
"""
set_of_very_common_units_in_SI = {
    ('radian',    'r',   '(1/(2*pi))',                            tuple(),                  ('radians',)),  # Note: here 'r' is used instead of the more common 'rad' to avoid collision
    ('steradian', 'sr',  '(1/(4*pi))',                            tuple(),                  ('steradians',)),
    ('minute',            'min', '(60*second)',                   tuple(),                  ('minutes',)),
    ('hour',              'h',   '(3600*second)',                 tuple(),                  ('hours',)),
    ('degree',            'deg', '(1/360)',                       tuple(),                  ('degrees',)),
    ('litre',             'L',   '(10**(-3)*metre**3)',           ('liter',),               ('litres,liters',)),
    ('metricton',         't',   '(10**3*kilogram)',              ('tonne',),               ('tonnes',)),
    ('neper',             'Np',  '(1)',                           ('Neper',),               ('nepers', 'Nepers')),
    ('bel',               'B',   '((1/2)*2.30258509299405)',      ('Bel',),                 ('bels', 'Bels')),  # Note: log(10) = 2.30258509299405 in base 2
    ('electronvolt',      'eV',  '(1.60218*10**(-19)*joule)',     tuple(),                  ('electronvolts',)),
    ('atomic_mass_unit',  'u',   '(1.66054*10**(-27)*kilogram)',  tuple(),                  ('atomic_mass_units',)),
    ('angstrom',          'Å',   '(10**(-10)*metre)',             ('Angstrom', 'Ångström'), ('angstroms', 'Angstroms')),
}


"""
Commonly used non-SI units taken from Table 6 and 7 https://physics.nist.gov/cuu/Units/outside.html
Note that short form symbols are defined here, but not used since they cause to many ambiguities
"""
set_of_common_units_in_SI = {
    ('day',               'd',   '(86400*second)',                     tuple(),                 ('days',)),
    ('angleminute',       "'",   '(pi/10800)',                         tuple(),                 tuple()),
    ('anglesecond',       '"',   '(pi/648000)',                        tuple(),                 tuple()),
    ('astronomical_unit', 'au',  '(149597870700*metre)',               tuple(),                 ('astronomical_units',)),
    ('nautical_mile',     'nmi', '(1852*metre)',                       tuple(),                 ('nauticalmiles',)),  # Note: no short form in source, short form from Wikipedia
    ('knot',              'kn',  '((1852/3600)*metre/second)',         tuple(),                 ('knots',)),  # Note: no short form in source, short form from Wikipedia
    ('are',               'a',   '(10**2*metre**2)',                   tuple(),                 ('ares',)),
    ('hectare',           'ha',  '(10**4*metre**2)',                   tuple(),                 ('hectares',)),
    ('bar',               'bar', '(10**5*pascal)',                     tuple(),                 ('bars',)),
    ('barn',              'b',   '(10**(-28)*metre**2)',               tuple(),                 ('barns',)),
    ('curie',             'Ci',  '(3.7*10**10*becquerel)',             ('Curie',),              ('curies',)),
    ('roentgen',          'R',   '(2.58*10**(-4)*kelvin/(kilogram))', ('Roentgen', 'Röntgen'), ('roentgens', 'Roentgens')),
    ('rad',               'rad', '(10**(-2)*gray)',                    tuple(),                 ('rads',)),
    ('rem',               'rem', '(10**(-2)*sievert)',                 tuple(),                 ('rems',)),
}

"""
Imperial (UK) units taken from https://en.wikipedia.org/wiki/Imperial_units and converted to SI base units
"""
set_of_imperial_units = {
    ('inch',              'in',    '(0.0254*metre)',              tuple(), ('inches',)),
    ('foot',              'ft',    '(0.3048*metre)',              tuple(), ('feet',)),
    ('yard',              'yd',    '(0.9144*metre)',              tuple(), ('yards',)),
    ('mile',              'mi',    '(1609.344*metre)',            tuple(), ('miles',)),
    ('fluid_ounce',       'fl_oz', '(0.00002841310625*metre**3)', tuple(), ('fluid_ounces',)),
    ('gill',              'gi',    '(0.0001420653125*metre**3)',  tuple(), ('gills',)),
    ('pint',              'pt',    '(0.00056826*metre**3)',       tuple(), ('pints',)),
    ('quart',             'qt',    '(0.0011365225*metre**3)',     tuple(), ('quarts',)),
    ('gallon',            'gal',   '(0.00454609*metre**3)',       tuple(), ('gallons',)),
    ('ounce',             'oz',    '(28.349523125*gram)',         tuple(), ('ounces',)),
    ('pound',             'lb',    '(0.45359237*kilogram)',       tuple(), ('pounds',)),
    ('stone',             'st',    '(6.35029318*kilogram)',       tuple(), tuple()),
}

"""
Conversion of other units to base SI
"""
non_base_units = set_of_common_units_in_SI | set_of_derived_SI_units_in_SI_base_units | set_of_very_common_units_in_SI | set_of_imperial_units
conversion_to_base_si_units = {x[0]: x[2] for x in non_base_units}
conversion_to_base_si_units.update({x[0]: x[0] for x in set_of_SI_base_unit_dimensions})
temp_dict = dict()
for item in set_of_SI_prefixes:
    temp_dict.update({item[0]+x: "("+item[2]+"*"+conversion_to_base_si_units[x]+")" for x in conversion_to_base_si_units.keys()})
conversion_to_base_si_units.update(temp_dict)
