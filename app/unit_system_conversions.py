# Remarks:
#   only K, no other temperature scales included
#   angles measures, bel an neper are all treated as identical dimensionless units

"""
Prefixes taken from Table 5 https://physics.nist.gov/cuu/Units/prefixes.html
"""
set_of_SI_prefixes = {
    ('yotta', 'Y',  '(10**24)'   ),
    ('zetta', 'Z',  '(10**21)'   ),
    ('exa',   'E',  '(10**18)'   ),
    ('peta',  'P',  '(10**15)'   ),
    ('tera',  'T',  '(10**12)'   ),
    ('giga',  'G',  '(10**9)'    ),
    ('mega',  'M',  '(10**6)'    ),
    ('kilo',  'k',  '(10**3)'    ),
    ('hecto', 'h',  '(10**2)'    ),
    ('deca',  'da', '(10**1)'    ),
    ('deci',  'd',  '(10**(-1))' ),
    ('centi', 'c',  '(10**(-2))' ),
    ('milli', 'm',  '(10**(-3))' ),
    ('micro', 'mu', '(10**(-6))' ),
    ('nano',  'n',  '(10**(-9))' ),
    ('pico',  'p',  '(10**(-12))'),
    ('femto', 'f',  '(10**(-15))'),
    ('atto',  'a',  '(10**(-18))'),
    ('zepto', 'z',  '(10**(-21))'),
    ('yocto', 'y',  '(10**(-24))')
}

"""
SI base units taken from Table 1 https://physics.nist.gov/cuu/Units/units.html
Note that gram is used as a base unit instead of kilogram.
"""
set_of_SI_base_unit_dimensions = {
    ('metre',   'm',   'length',              ('metres','meter','meters')),
    ('gram',    'g',   'mass',                ('grams')),
    ('second',  's',   'time',                ('seconds')),
    ('ampere',  'A',   'electric_current',    ('amperes','Ampere','Amperes')),
    ('kelvin',  'K',   'temperature',         ('kelvins','Kelvin','Kelvins')),
    ('mole',    'mol', 'amount_of_substance', ('moles')),
    ('candela', 'cd',  'luminous_intensity',  ('candelas','Candela','Candelas')),
}

"""
Derived SI units taken from Table 3 https://physics.nist.gov/cuu/Units/units.html
Note that radians and degree have been moved to list_of_very_common_units_in_SI to reduce collisions when substituting.
Note that degrees Celsius is omitted.
"""
set_of_derived_SI_units_in_SI_base_units = {
    ('hertz',     'Hz',  '(second**(-1))',                                      tuple()),
    ('newton',    'N',   '(metre*kilo*gram*second**(-2))',                      ('newtons','Newton','Newtons')),
    ('pascal',    'Pa',  '(metre**(-1)*kilogram*second**(-2))',                 ('pascals','Pascal','Pascals')),
    ('joule',     'J',   '(metre**2*kilo*gram*second**(-2))',                   ('joules','Joule','Joules')),
    ('watt',      'W',   '(metre**2*kilo*gram*second**(-3))',                   ('watts','Watt','Watts')),
    ('coulomb',   'C',   '(second*ampere)',                                     ('coulombs','Coulomb','Coulombs')),
    ('volt',      'V',   '(metre**2*kilo*gram*second**(-3)*ampere**(-1))',      ('volts','Volt','Volts')),
    ('farad',     'F',   '(metre**(-2)*(kilo*gram)**(-1)*second**4*ampere**2)', ('farads','Farad','Farads')),
    ('ohm',       'O', '(metre**2*kilo*gram*second**(-3)*ampere**(-2))',        ('ohms','Ohm','Ohms')),
    ('siemens',   'S',   '(metre**(-2)*kilo*gram**(-1)*second**3*ampere**2)',   ('Siemens')),
    ('weber',     'Wb',  '(metre**2*kilo*gram*second**(-2)*ampere**(-1))',      ('webers','Weber','Webers')),
    ('tesla',     'T',   '(kilo*gram*second**(-2)*ampere**(-1))',               ('teslas','Tesla','Teslas')),
    ('henry',     'H',   '(metre**2*kilo*gram*second**(-2)*ampere**(-2))',      ('henrys','Henry','Henrys')),
    ('lumen',     'lm',  '(candela)',                                           ('lumens')),
    ('lux',       'lx',  '(metre**(-2)*candela)',                               tuple()),
    ('becquerel', 'Bq',  '(second**(-1))',                                      ('becquerels','Becquerel','Becquerels')),
    ('gray',      'Gy',  '(metre**2*second**(-2))',                             ('grays','Gray','Grays')),
    ('sievert',   'Sv',  '(metre**2*second**(-2))',                             ('sieverts','Sievert','Sieverts')),
    ('katal',     'kat', '(second**(-1)*mole)',                                 ('katals','Katal','Katals'))
}

"""
Commonly used non-SI units taken from Table 6 and 7 https://physics.nist.gov/cuu/Units/outside.html
Note that radian and steradian from Table 3 have been moved here to reduce collisions when substituting.
This is the subset of common symbols whose short form symbols are allowed
"""
set_of_very_common_units_in_SI = {
    ('radian',    'r',   '(1)',                                   ('radians')), # Note: here 'r' is used instead of the more common 'rad' to avoid collision
    ('steradian', 'sr',  '(1)',                                   ('steradians')),
    ('minute',            'min', '(60*second)',                   ('minutes')),
    ('hour',              'h',   '(3600*second)',                 ('hours')),
    ('degree',            'deg', '(pi/180)',                      ('degrees')),
    ('liter',             'L',   '(10**(-3)*metre**3)',           ('liters')),
    ('metricton',         't',   '(10**3*kilo*gram)',             ('tonne','tonnes')),
    ('neper',             'Np',  '(1)',                           ('nepers','Neper','Nepers')),
    ('bel',               'B',   '((1/2)*log(10))',               ('bels','Bel','Bels')),
    ('electronvolt',      'eV',  '(1.60218*10**(-19)*joule)',     ('electronvolts')),
    ('atomicmassunit',    'u',   '(1.66054*10**(-27)*kilo*gram)', ('atomicmassunits')),
    ('angstrom',          'Å',   '(10**(-10)*metre)',             ('angstroms','Angstrom','Angstroms','Ångström')),
}


"""
Commonly used non-SI units taken from Table 6 and 7 https://physics.nist.gov/cuu/Units/outside.html
Note that short form symbols are defined here, but not used since they cause to many ambiguities
"""
set_of_common_units_in_SI = {
    ('day',               'd',   '(86400*second)',                     ('days')),
    ('angleminute',       "'",   '(pi/10800)',                         tuple()),
    ('anglesecond',       '"',   '(pi/648000)',                        tuple()),
    ('astronomicalunit',  'au',  '(149597870700*metre)',               ('astronomicalunits')),
    ('nauticalmile',      'nmi', '(1852*metre)',                       ('nauticalmiles')), #Note: no short form in source, short form from Wikipedia
    ('knot',              'kn',  '((1852/3600)*metre/second)',         ('knots')), #Note: no short form in source, short form from Wikipedia
    ('are',               'a',   '(10**2*metre**2)',                   ('ares')),
    ('hectare',           'ha',  '(10**4*metre**2)',                   ('hectares')),
    ('bar',               'bar', '(10**5*pascal)',                     ('bars')),
    ('barn',              'b',   '(10**(-28)*metre**2)',               ('barns')),
    ('curie',             'Ci',  '(3.7*10**10*becquerel)',             ('curies')),
    ('roentgen',          'R',   '(2.58*10**(-4)*kelvin/(kilo*gram))', ('roentgens','Roentgen','Roentgens','Röntgen')),
    ('rad',               'rad', '(10**(-2)*gray)',                    ('rads')),
    ('rem',               'rem', '(10**(-2)*sievert)',                 ('rems')),
}

"""
Imperial (UK) units taken from https://en.wikipedia.org/wiki/Imperial_units
"""
set_of_imperial_units = {
    ('inch',              'in',   '(0.0254*metre)',                    ('inches')),
    ('foot',              'ft',   '(0.3048*metre)',                    ('feet')),
    ('yard',              'yd',   '(0.9144*metre)',                    ('yards')),
    ('mile',              'mi',   '(1609.344*metre)',                  ('miles')),
    ('fluid ounce',       'fl oz','(28.4130625*milli*litre)',          ('fluid ounces')),
    ('gill',              'gi',   '(142.0653125*milli*litre)',         ('gills')),
    ('pint',              'pt',   '(568.26125*milli*litre)',           ('pints')),
    ('quart',             'qt',   '(1.1365225*litre)',                 ('quarts')),
    ('gallon',            'gal',  '(4546.09*litre)',                   ('gallons')),
    ('ounce',             'oz',   '(28.349523125*gram)',               ('ounces')),
    ('pound',             'lb',   '(0.45359237*kilo*gram)',            ('pounds')),
    ('stone',             'st',   '(6.35029318*kilo*gram)',            tuple()),
}