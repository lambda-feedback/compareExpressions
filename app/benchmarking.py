benchmarks = [
    {
        "response": "2a",
        "answer": "a",
        "params": {
            "strict_syntax": False,
            "elementary_functions": True,
            "criteria": "response/answer=2",
        }
    },
    {
        "response": "2*x**2 = 10*y**2+20",
        "answer": "x**2-5*y**2-10=0",
        "params": {"strict_syntax": False}
    },
    {
        "response": "1.24 mile/hour",
        "answer": "1.24 mile/hour",
        "params": {
            "strict_syntax": False,
            "elementary_functions": True,
            "physical_quantity": True,
        }
    },
    {
        "response": "sin(x)+2",
        "answer": "sin(x)",
        "params": {
            "strict_syntax": False,
            "elementary_functions": True,
            "criteria": "Derivative(response,x)=cos(x)",
        }
    },
    {
        "response": "cos(x)**2 + sin(x)**2 + y",
        "answer": "y + 1",
        "params": {"strict_syntax": False}
    },
    {
        "response": "log(2)/2+I*(3*pi/4 plus_minus 2*n*pi)",
        "answer": "log(2)/2+I*(3*pi/4 plus_minus 2*n*pi)",
        "params": {
                "strict_syntax": False,
                "elementary_functions": True,
            }
    },
    {
        "response": "6*cos(5*x+1)-90*x*sin(5*x+1)-225*x**2*cos(5*x+1)+125*x**3*sin(5*x+1)",
        "answer": "6*cos(5*x+1)-90*x*sin(5*x+1)-225*x**2*cos(5*x+1)+125*x**3*sin(5*x+1)",
        "params": {"strict_syntax": False}
    },
    {
        "response": "-(sin(xy)y+(e^y))/(x(e^y+sin(xy)x))",
        "answer": "-(y*sin(x*y) + e^(y)) / (x*(e^(y) + sin(x*y)))",
        "params": {"strict_syntax": False}
    },
]
