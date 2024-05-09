import json
from deepdiff import DeepDiff
from rich.console import Console
import logging
import os
import subprocess
import time

logger = logging.getLogger('finisterra')


def count_resources_by_action_and_collect_changes(plan):
    actions_count = {
        "import": 0,
        "add": 0,
        "update": 0,
        "destroy": 0,
    }
    updates_details = {}

    data = json.loads(plan)

    for resource in data.get("resource_changes", []):
        change = resource.get("change", {})
        actions = change.get("actions", [])

        if 'importing' in change:
            actions_count["import"] += 1

        for action in actions:
            if action == "create":
                actions_count["add"] += 1
            elif action == "update":
                actions_count["update"] += 1
                before = change.get("before", {})
                after = change.get("after", {})
                if before and after:  # Only if there are changes
                    updates_details[resource.get('address')] = DeepDiff(
                        before, after, ignore_order=True, verbose_level=2).to_dict()
            elif action == "delete":
                actions_count["destroy"] += 1

    return actions_count, updates_details


def print_title(title):
    console = Console()
    console.print(f"[bold][white]{title}[/white][/bold]")


def normalize_text(value):
    # Example normalization for configuration strings:
    # Ensures consistent spacing around '=' for key-value pairs
    if isinstance(value, str) and '=' in value:
        return '\n'.join([line.strip().replace(" = ", "=").replace("= ", "=").replace(" =", "=") for line in value.split('\n')])
    return value


def print_detailed_changes(counts, updates, known_okay_changes=None):
    known_okay_changes = [
        "['default_action'][0]['target_group_arn']", "['action'][0]['target_group_arn']", "['default_action'][0]['forward'][0]"]
    console = Console()

    for address, changes in updates.items():
        real_update = False
        for change_key in ["type_changes", "values_changed"]:
            if change_key in changes:
                for change_detail in changes[change_key]:
                    item_path = change_detail.split('root')[1]
                    if item_path in known_okay_changes:
                        continue

                    old_value = changes[change_key][change_detail]['old_value']
                    new_value = changes[change_key][change_detail]['new_value']

                    # Normalize values to ignore whitespace and newline differences only if they are strings
                    old_value_normalized = normalize_text(old_value).replace(' ', '').replace(
                        '\n', '') if isinstance(old_value, str) else old_value
                    new_value_normalized = normalize_text(new_value).replace(' ', '').replace(
                        '\n', '') if isinstance(new_value, str) else new_value

                    # Attempt to parse JSON if the values are normalized strings
                    old_value_obj, new_value_obj = None, None
                    if isinstance(old_value_normalized, str):
                        try:
                            old_value_obj = json.loads(old_value_normalized)
                        except json.JSONDecodeError:
                            old_value_obj = old_value_normalized

                    if isinstance(new_value_normalized, str):
                        try:
                            new_value_obj = json.loads(new_value_normalized)
                        except json.JSONDecodeError:
                            new_value_obj = new_value_normalized

                    # Compare the Python objects or normalized text directly
                    if old_value_obj == new_value_obj:
                        # If the objects or text are equal, the difference is only in formatting
                        continue

                    if not real_update:
                        print_title(f"{address} will be updated in-place:")
                        real_update = True
                    console.print(f"  [orange3]{item_path}[/orange3]")
                    console.print(
                        f"    ~ [white]From: [/white][orange3]{json.dumps(old_value, indent=4, default=str)}[/orange3]")
                    console.print(
                        f"    ~ [white]To: [/white][orange3]{json.dumps(new_value, indent=4, default=str)}[/orange3]")

        # Handle added items
        if 'dictionary_item_added' in changes or 'iterable_item_added' in changes:
            added_key = 'dictionary_item_added' if 'dictionary_item_added' in changes else 'iterable_item_added'
            for change_detail in changes[added_key]:
                item_path = change_detail.split('root')[1]
                if item_path in known_okay_changes:
                    continue
                if not real_update:
                    print_title(f"{address} will be updated in-place:")
                    real_update = True
                value_added = changes[added_key][change_detail]
                console.print(f"[green]  + {item_path}[/green]")
                console.print(
                    f"    + [green]{json.dumps(value_added, indent=4)}[/green]")

        # Handle removed items
        if 'dictionary_item_removed' in changes or 'iterable_item_removed' in changes:
            removed_key = 'dictionary_item_removed' if 'dictionary_item_removed' in changes else 'iterable_item_removed'
            for change_detail in changes[removed_key]:
                item_path = change_detail.split('root')[1]
                if item_path in known_okay_changes:
                    continue
                if not real_update:
                    print_title(f"{address} will be updated in-place:")
                    real_update = True
                value_removed = changes[removed_key][change_detail]
                console.print(f"[red]  - {item_path}[/red]")
                console.print(
                    f"    - [red]{json.dumps(value_removed, indent=4)}[/red]")

        if not real_update:
            if counts["update"] > 0:
                counts["update"] -= 1

    return counts


def print_summary(counts, module):
    console = Console()
    action_colors = {
        "import": "green",
        "add": "green",
        "update": "orange3",
        "destroy": "red",
        "no-op": "grey"
    }

    console.print(
        f"[bold][white]{module}[/white][/bold]", end=": ")
    for action, count in counts.items():
        if count > 0:
            console.print(
                f"[{action_colors[action]}]{count} to {action.title()}, ", end="")
        else:
            console.print(f"[white]{count} to {action.title()}, ", end="")
    console.print()  # For newline at the end


def print_tf_plan(counts, updates, module):
    counts = print_detailed_changes(counts, updates)
    print_summary(counts, module)
    return counts


def execute_terraform_plan(console, output_dir, ftstack):
    # Define the working directory for this ftstack
    cwd = os.path.join(output_dir, "tf_code", ftstack)

    max_retries = 1  # Maximum number of retries
    retry_count = 0  # Initial retry count

    while retry_count <= max_retries:
        try:
            logger.info(
                f"Running Terraform plan on the generated code for {ftstack}...")
            # Run terraform init with the specified working directory
            subprocess.run(["terragrunt", "init", "-no-color"], cwd=cwd, check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Run terraform plan with the specified working directory
            plan_file_name = os.path.join(cwd, f"{ftstack}_plan")
            subprocess.run(["terragrunt", "plan", "-no-color", "-out", plan_file_name],
                           cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Run terraform show with the specified working directory
            json_file_name = os.path.join(cwd, f"{ftstack}_plan.json")
            subprocess.run(f"terragrunt show -json {plan_file_name} > {json_file_name}",
                           shell=True, cwd=cwd, check=True, stderr=subprocess.PIPE)
            # Read and process the Terraform plan JSON
            with open(json_file_name) as f:
                counts, updates = count_resources_by_action_and_collect_changes(
                    f.read())
            # clean up the plan files
            os.remove(plan_file_name)
            os.remove(json_file_name)
            return (counts, updates, ftstack)
        except FileNotFoundError as e:
            return None
        except subprocess.CalledProcessError as e:
            console.print(
                f"[red]Error in Terraform operation for {ftstack}: {e.stderr.decode('utf-8')}[/red]")
            if retry_count < max_retries:
                retry_count += 1
                console.print(
                    f"[yellow]Retrying Terraform init and plan for {ftstack} in 10 seconds...[/yellow]")
                time.sleep(10)  # Wait for 10 seconds before retrying
            else:
                return None
