# Base image that bundles the AWS Lambda Python image with the lambda-feedback middleware (app.handler)
FROM ghcr.io/lambda-feedback/baseevalutionfunctionlayer:main-3.12

RUN dnf install -y git findutils && dnf clean all

WORKDIR /app

ENV PYTHONPATH=/app

# Copy and install any packages/modules needed for your evaluation script.
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# The healthcheck command runs the pytest suite (see evaluation_tests.py)
RUN pip3 install pytest

# Copy the evaluation function source, tests and docs (exclusions in .dockerignore)
COPY . ./app/

# Set permissions so files and directories can be accessed on AWS
RUN chmod 644 $(find . -type f)
RUN chmod 755 $(find . -type d)

# The entrypoint for AWS is to invoke the handler function within the app package
CMD [ "app.handler" ]
