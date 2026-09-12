# Base image that bundles AWS Lambda Python 3.8 image with some middleware functions
# FROM base-eval-tmp
# FROM rabidsheep55/python-base-eval-layer
FROM ghcr.io/lambda-feedback/baseevalutionfunctionlayer:main-3.12

RUN dnf install -y git findutils && dnf clean all

WORKDIR /app

ENV PYTHONPATH=/app

# Copy and install any packages/modules needed for your evaluation script.
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Copy main scripts
COPY evaluation.py ./app/
COPY evaluation_test.py ./app/
COPY preview.py ./app/
COPY preview_test.py ./app/
COPY result.py ./app/

# Copy contexts
COPY context/physical_quantity.py ./app/context/
COPY context/symbolic.py ./app/context/

# Copy feedback messages
COPY feedback/physical_quantity.py ./app/feedback/
COPY feedback/symbolic.py ./app/feedback/

# Copy tests
COPY tests/example_test.py ./app/tests/
COPY tests/physical_quantity_evaluation_test.py ./app/tests/
COPY tests/physical_quantity_test_cases.py ./app/tests/
COPY tests/symbolic_evaluation_test.py ./app/tests/

# Copy Documentation
COPY docs/dev.md ./app/docs/dev.md
COPY docs/user.md ./app/docs/user.md

# Set permissions so files and directories can be accessed on AWS
RUN chmod 644 $(find . -type f)
RUN chmod 755 $(find . -type d)

# The entrypoint for AWS is to invoke the handler function within the app package
CMD [ "app.handler" ]
