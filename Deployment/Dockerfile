FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.12

# Install build dependencies for C-extensions (like hnswlib/chromadb required by crewai)
RUN dnf install -y gcc gcc-c++ make && \
    dnf clean all

# Install uv
RUN pip install uv

# Copy project definition files
COPY pyproject.toml uv.lock ${LAMBDA_TASK_ROOT}/

# Copy the application source code BEFORE installing the package
COPY src ${LAMBDA_TASK_ROOT}/src
COPY knowledge ${LAMBDA_TASK_ROOT}/knowledge

# Install the package and its dependencies
RUN uv pip install --system --no-cache --target ${LAMBDA_TASK_ROOT} .

# Copy the lambda handler script we created
COPY Deployment/lambda_function.py ${LAMBDA_TASK_ROOT}/lambda_function.py

# Set the entrypoint command for lambda
CMD [ "lambda_function.lambda_handler" ]