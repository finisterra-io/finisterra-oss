import os
import subprocess


def is_valid_github_repo(local_repo_path):
    # Step 1: Check if the directory exists
    if not os.path.isdir(local_repo_path):
        print("Directory does not exist.")
        return False

    # Step 2: Check if the directory is a Git repository with a GitHub remote
    try:
        result = subprocess.run(["git", "-C", local_repo_path, "remote", "-v"],
                                stdout=subprocess.PIPE, check=True, text=True)
        remotes = result.stdout
        if "github.com" in remotes:
            print("Directory is a valid GitHub repository.")
            return True
        else:
            print("Directory is not a GitHub repository.")
            return False
    except subprocess.CalledProcessError:
        print("Failed to execute Git command. Make sure the directory is a Git repository.")
        return False
