# Base image that bundles AWS Lambda Python 3.8 image with some middleware functions
# FROM base-eval-tmp
FROM rabidsheep55/python-base-eval-layer

RUN yum install -y git

WORKDIR /app

# Copy and install any packages/modules needed for your evaluation script.
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy scripts
COPY comparison_utilities.py ./app/
COPY criteria_utilities.py ./app/
COPY evaluation.py ./app/
COPY evaluation_response_utilities.py ./app/
COPY evaluation_tests.py ./app/
COPY example_tests.py ./app/
COPY symbolic_comparison_preview.py ./app/
COPY symbolic_comparison_preview_tests.py ./app/
COPY expression_utilities.py ./app/
COPY preview.py ./app/
COPY preview_tests.py ./app/
COPY preview_utilities.py ./app/
COPY quantity_comparison_preview.py ./app/
COPY quantity_comparison_preview_tests.py ./app/
COPY quantity_comparison_evaluation_tests.py ./app/
COPY slr_parsing_utilities.py ./app/
COPY slr_quantity.py ./app/
COPY slr_quantity_tests.py ./app/
COPY symbolic_comparison_evaluation.py ./app/
COPY symbolic_comparison_evaluation_tests.py ./app/
COPY unit_system_conversions.py ./app/

# Copy feedback messages
COPY feedback/quantity_comparison.py ./app/feedback/
COPY feedback/symbolic_comparison.py ./app/feedback/

# Copy Documentation
COPY docs/dev.md ./app/docs/dev.md
COPY docs/user.md ./app/docs/user.md
COPY docs/quantity_comparison_graph.svg ./app/docs/quantity_comparison_graph.svg

# Set permissions so files and directories can be accessed on AWS
RUN chmod 644 $(find . -type f)
RUN chmod 755 $(find . -type d)

# The entrypoint for AWS is to invoke the handler function within the app package
CMD [ "/app/app.handler" ]
