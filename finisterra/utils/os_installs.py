import platform
import os
import subprocess
import logging

logger = logging.getLogger('finisterra')


def get_os():
    if os.name == 'nt':
        return 'Windows'
    elif os.name == 'posix':
        if platform.system() == 'Darwin':
            return 'macOS'
        else:
            return 'Linux'
    else:
        return 'Unknown'


def is_gh_installed():
    try:
        subprocess.run(["gh", "--version"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_gh():
    try:
        if not is_gh_installed():
            os_name = get_os()
            logger.info(f"Installing GitHub CLI on {os_name}...")
            if os_name == 'Windows':
                subprocess.run(["scoop", "install", "gh"], check=True)
            elif os_name == 'macOS':
                subprocess.run(["brew", "install", "gh"], check=True)
            elif os_name == 'Linux':
                # Adjust for your preferred package manager
                subprocess.run(["sudo", "apt", "install", "gh"], check=True)
            print("GitHub CLI installed successfully.")
    except subprocess.CalledProcessError as e:
        print("Failed to install GitHub CLI:", e)
