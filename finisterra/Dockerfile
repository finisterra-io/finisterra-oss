# Use the official Python 3.9-slim image as a parent image
FROM python:3.11-slim

# Set the working directory in the Docker container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install system utilities required for downloading Terraform and Terragrunt, and also install git
RUN apt-get update && apt-get install -y wget unzip git && rm -rf /var/lib/apt/lists/*

# Install Terraform
RUN TERRAFORM_VERSION="1.5.0" && \
    wget https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    unzip terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    mv terraform /usr/local/bin/ && \
    rm terraform_${TERRAFORM_VERSION}_linux_amd64.zip

# Install Terragrunt
RUN TERRAGRUNT_VERSION="0.50.4" && \
    wget https://github.com/gruntwork-io/terragrunt/releases/download/v${TERRAGRUNT_VERSION}/terragrunt_linux_amd64 && \
    chmod +x terragrunt_linux_amd64 && \
    mv terragrunt_linux_amd64 /usr/local/bin/terragrunt

# Upgrade pip
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Set the default command to python3
ENTRYPOINT ["python3"]

