import json
from deepdiff import DeepDiff  # Make sure to install deepdiff first
from rich.console import Console
from rich.table import Table


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


def print_detailed_changes(updates):
    console = Console()

    for address, changes in updates.items():
        console.print(
            f"\n[white]{address} will be updated in-place:[/white]")
        # Handle changes in values
        if 'type_changes' in changes:
            for change_detail in changes['type_changes']:
                item_path = change_detail.split('root')[1]
                old_value = changes['type_changes'][change_detail]['old_value']
                new_value = changes['type_changes'][change_detail]['new_value']
                console.print(f"  [orange3]{item_path}[/orange3]")
                console.print(
                    f"    ~ [orange3]{json.dumps(old_value, indent=4)} => {json.dumps(new_value, indent=4)}[/orange3]")

        if 'values_changed' in changes:
            for change_detail in changes['values_changed']:
                item_path = change_detail.split('root')[1]
                old_value = changes['values_changed'][change_detail]['old_value']
                new_value = changes['values_changed'][change_detail]['new_value']
                console.print(f"  [orange3]{item_path}[/orange3]")
                console.print(
                    f"    ~ [orange3]{json.dumps(old_value, indent=4)} => {json.dumps(new_value, indent=4)}[/orange3]")

        # Handle added items
        if 'dictionary_item_added' in changes or 'iterable_item_added' in changes:
            added_key = 'dictionary_item_added' if 'dictionary_item_added' in changes else 'iterable_item_added'
            for change_detail in changes[added_key]:
                item_path = change_detail.split('root')[1]
                value_added = changes[added_key][change_detail]
                console.print(f"[green]  + {item_path}[/green]")

        # Handle removed items
        if 'dictionary_item_removed' in changes or 'iterable_item_removed' in changes:
            removed_key = 'dictionary_item_removed' if 'dictionary_item_removed' in changes else 'iterable_item_removed'
            for change_detail in changes[removed_key]:
                item_path = change_detail.split('root')[1]
                value_removed = changes[removed_key][change_detail]
                console.print(f"[red]  - {item_path}[/red]")


def print_summary(counts, module):
    console = Console()
    action_colors = {
        "import": "green",
        "add": "green",
        "update": "orange3",
        "destroy": "red",
        "no-op": "grey"
    }

    for action, count in counts.items():
        if count > 0:
            console.print(
                f"[{action_colors[action]}]{count} to {action.title()}, ", end="")
        else:
            console.print(f"[white]{count} to {action.title()}, ", end="")
    console.print()  # For newline at the end


# Example usage:
if __name__ == "__main__":
    with open('/tmp/ncm/tf_code/eks/eks_plan.json', 'r') as file:
        terraform_plan = file.read()

    counts, updates = count_resources_by_action_and_collect_changes(
        terraform_plan)

    print_summary(counts, "Module")
    print_detailed_changes(updates)
