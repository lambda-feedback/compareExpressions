# Base image that bundles AWS Lambda Python 3.8 image with some middleware functions
# FROM base-eval-tmp
FROM rabidsheep55/python-base-eval-layer

RUN yum install -y git

WORKDIR /app

# Copy and install any packages/modules needed for your evaluation script.
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy main scripts
COPY evaluation.py ./app/
COPY evaluation_tests.py ./app/
COPY preview.py ./app/
COPY preview_tests.py ./app/

# Copy contexts
COPY context/physical_quantity.py ./app/context/
COPY context/symbolic.py ./app/context/

# Copy feedback messages
COPY feedback/physical_quantity.py ./app/feedback/
COPY feedback/symbolic.py ./app/feedback/

# Copy preview implementations
COPY preview_implementations/physical_quantity_preview.py ./app/preview_implementations/
COPY preview_implementations/symbolic_preview.py ./app/preview_implementations/

# Copy tests
COPY tests/example_tests.py ./app/tests/
COPY tests/physical_quantity_evaluation_tests.py ./app/tests/
COPY tests/physical_quantity_preview_tests.py ./app/tests/
COPY tests/slr_quantity_tests.py ./app/tests/
COPY tests/symbolic_evaluation_tests.py ./app/tests/
COPY tests/symbolic_preview_tests.py ./app/tests/

# Copy utility code
COPY utility/criteria_graph_utilities.py ./app/utility/
COPY utility/criteria_parsing.py ./app/utility/
COPY utility/evaluation_result_utilities.py ./app/utility/
COPY utility/expression_utilities.py ./app/utility/
COPY utility/physical_quantity_utilities.py ./app/utility/
COPY utility/preview_utilities.py ./app/utility/
COPY utility/slr_parsing_utilities.py ./app/utility/
COPY utility/syntactical_comparison_utilities.py ./app/utility/
COPY utility/unit_system_conversions.py ./app/utility/

# Copy Documentation
COPY docs/dev.md ./app/docs/dev.md
COPY docs/user.md ./app/docs/user.md
COPY docs/quantity_comparison_graph.svg ./app/docs/quantity_comparison_graph.svg

# Set permissions so files and directories can be accessed on AWS
RUN chmod 644 $(find . -type f)
RUN chmod 755 $(find . -type d)

# The entrypoint for AWS is to invoke the handler function within the app package
CMD [ "/app/app.handler" ]
