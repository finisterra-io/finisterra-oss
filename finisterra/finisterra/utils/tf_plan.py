import json
from deepdiff import DeepDiff  # Make sure to install deepdiff first
from rich.console import Console
import logging

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

# # Example usage:
# if __name__ == "__main__":
#     with open('/tmp/ncm/tf_code/eks/eks_plan.json', 'r') as file:
#         terraform_plan = file.read()

#     counts, updates = count_resources_by_action_and_collect_changes(
#         terraform_plan)

#     print_summary(counts, "Module")
#     print_detailed_changes(updates)
