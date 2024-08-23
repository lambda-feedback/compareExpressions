# YourFunctionName

This function utilises the [`SymPy`](https://docs.sympy.org/latest/index.html) to provide a maths-aware comparsion of a student's response to the correct answer. This means that mathematically equivalent inputs will be marked as correct. Note that `pi` is a reserved constant and cannot be used as a symbol name.

Note that this function is designed to handle comparisons of mathematical expressions but has some limited ability to handle comparison of equalities as well. More precisely, if the answer is of the form $f(x_1,\ldots,x_n) = g(x_1,\ldots,x_n)$ and the response is of the form $\tilde{f}(x_1,\ldots,x_n) = \tilde{g}(x_1,\ldots,x_n)$ then the function checks if $f(x_1,\ldots,x_n) - g(x_1,\ldots,x_n)$ is a multiple of $\tilde{f}(x_1,\ldots,x_n) / \tilde{g}(x_1,\ldots,x_n)$.

For details and examples on intended usage see user documentation: [User documentation for compareExpressions](https://lambda-feedback.github.io/user-documentation/user_eval_function_docs/compareExpressions/#compareexpressions)

## Inputs
*Specific input parameters which can be supplied when the `eval` command is supplied to this function.*

## Outputs
*Output schema/values for this function*

## Examples
*List of example inputs and outputs for this function, each under a different sub-heading*

### Simple Evaluation

```python
{
  "example": {
    "Something": "something"
  }
}
```

```python
{
  "example": {
    "Something": "something"
  }
}
```