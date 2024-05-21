# Pull the base image with Node.js
FROM node:16-alpine

# Set the working directory in the Docker container
WORKDIR /usr/src/app

# Copy the package.json and package-lock.json (if available)
COPY package*.json ./

# Install Python and other dependencies
RUN apk add --no-cache python3 make g++ git postgresql-client

# Install the application dependencies
RUN npm install

# Set up a git user
RUN git config --global user.email "code@finisterra.io"
RUN git config --global user.name "finisterra"

# Install Terraform
RUN apk add --no-cache unzip curl \
    && curl -o terraform.zip https://releases.hashicorp.com/terraform/1.0.5/terraform_1.0.5_linux_amd64.zip \
    && unzip terraform.zip \
    && mv terraform /usr/local/bin/ \
    && rm -f terraform.zip

# Copy the rest of the application code
COPY . .

# Copy the entrypoint script
COPY ./bin/entrypoint.sh .

# Build the application
ARG NEXT_PUBLIC_GITHUB_APP_NAME
ARG NEXT_PUBLIC_BASE_URL
ARG NEXT_PUBLIC_STRIPE_PUBLIC_KEY

ENV NEXT_PUBLIC_GITHUB_APP_NAME=$NEXT_PUBLIC_GITHUB_APP_NAME
ENV NEXT_PUBLIC_BASE_URL=$NEXT_PUBLIC_BASE_URL
ENV NEXT_PUBLIC_STRIPE_PUBLIC_KEY=$NEXT_PUBLIC_STRIPE_PUBLIC_KEY

RUN npm install -g prisma && prisma generate
RUN npm run build

# Expose port 3000 to have it mapped by Docker daemon
EXPOSE 3000

# Command to run the entrypoint script
ENTRYPOINT ["sh", "./bin/entrypoint.sh"]
