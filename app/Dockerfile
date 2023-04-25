# Base image that bundles AWS Lambda Python 3.8 image with some middleware functions
# FROM base-eval-tmp
FROM rabidsheep55/python-base-eval-layer

WORKDIR /app

# Copy and install any packages/modules needed for your evaluation script.
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy the evaluation and testing scripts
COPY comparison_utilities.py ./app/
COPY evaluation.py ./app/
COPY evaluation_response_utilities.py ./app/
COPY evaluation_tests.py ./app/
COPY expression_utilities.py ./app/
COPY feedback/physical_quantities.py ./app/feedback/
COPY slr_parsing_utilities.py ./app/
COPY slr_quantity.py ./app/
COPY slr_quantity_tests.py ./app/
COPY symbolic_equal.py ./app/
COPY unit_system_conversions.py ./app/

# Copy Documentation
COPY docs/dev.md ./app/docs/dev.md
COPY docs/user.md ./app/docs/user.md

# Set permissions so files and directories can be accessed on AWS
RUN chmod 644 $(find . -type f)
RUN chmod 755 $(find . -type d)

# The entrypoint for AWS is to invoke the handler function within the app package
CMD [ "/app/app.handler" ]
