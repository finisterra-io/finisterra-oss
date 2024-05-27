#!/usr/bin/env bash

set -e

# Function to check if command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Detect OS and set package manager and installation commands
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PACKAGE_MANAGER="apt"
    INSTALL_CMD="sudo apt install -y"
    UPDATE_CMD="sudo apt update"
    DOCKER_GPG_CMD="curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo -E apt-key add -"
    DOCKER_REPO_CMD='sudo add-apt-repository -y "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"'
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PACKAGE_MANAGER="brew"
    INSTALL_CMD="brew install"
    UPDATE_CMD=""
    DOCKER_GPG_CMD=""
    DOCKER_REPO_CMD=""
else
    echo "Unsupported OS type: $OSTYPE"
    exit 1
fi

# Automatically restart without asking
export DEBIAN_FRONTEND=noninteractive
export RESTART_MODE=l

# Update package list
echo "Updating package list..."
$UPDATE_CMD

# Setup Docker
if ! command_exists docker; then
    echo "Docker is not installed. Setting up Docker."
    
    if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
        $INSTALL_CMD apt-transport-https ca-certificates curl software-properties-common
        eval "$DOCKER_GPG_CMD"
        eval "$DOCKER_REPO_CMD"
        $UPDATE_CMD
        sudo apt-cache policy docker-ce
        $INSTALL_CMD docker-ce
    elif [[ "$PACKAGE_MANAGER" == "brew" ]]; then
        $INSTALL_CMD docker
    fi
else
    echo "Docker is already installed. Skipping installation."
fi

# Enable Docker without sudo on Linux
if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
    sudo usermod -aG docker "${USER}" || true
fi

# Setup Docker Compose
if ! command_exists docker-compose; then
    echo "Setting up Docker Compose"
    if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
        sudo curl -L "https://github.com/docker/compose/releases/download/v2.13.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose || true
        sudo chmod +x /usr/local/bin/docker-compose
    elif [[ "$PACKAGE_MANAGER" == "brew" ]]; then
        $INSTALL_CMD docker-compose
    fi
else
    echo "Docker Compose is already installed. Skipping installation."
fi

# Setup Git
if ! command_exists git; then
    echo "Git is not installed. Setting up Git."
    $INSTALL_CMD git
else
    echo "Git is already installed. Skipping installation."
fi

# Clone Finisterra repository
echo "Installing Finisterra from Github..."
git clone https://github.com/finisterra-io/finisterra.git &> /dev/null || true
cd finisterra
echo "Pulling the latest changes from Github..."
git pull origin main &> /dev/null || true

# Start the application
cd frontend
docker-compose -f docker-compose.yml up  --build
