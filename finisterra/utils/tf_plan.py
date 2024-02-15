import json
from rich import print
from rich.console import Console
from rich.table import Table

# Function to identify and return detailed changes for updated resources
def identify_detailed_changes(before, after):
    detailed_changes = {}
    all_keys = set(before.keys()) | set(after.keys())
    for key in all_keys:
        before_value = before.get(key, "N/A (new field)")
        after_value = after.get(key, "N/A (removed field)")
        if before_value != after_value:
            detailed_changes[key] = {
                "from": before_value,
                "to": after_value
            }
    return detailed_changes

# Function to count resources by action and collect detailed changes for updates
def count_resources_by_action_and_collect_changes(plan):
    actions_count = {
        "imported": 0,
        "added": 0,
        "updated": 0,
        "destroyed": 0,
    }
    updates_details = {}
    
    data = json.loads(plan)

    for resource in data.get("resource_changes", []):
        change = resource.get("change", {})
        actions = change.get("actions", [])
        
        if 'importing' in change:
            actions_count["imported"] += 1
        
        for action in actions:
            if action == "create":
                actions_count["added"] += 1
            elif action == "update":
                actions_count["updated"] += 1
                detailed_changes = identify_detailed_changes(change.get("before", {}), change.get("after", {}))
                updates_details[resource.get('address')] = detailed_changes
            elif action == "delete":
                actions_count["destroyed"] += 1
                
    return actions_count, updates_details

def print_detailed_changes(updates):
    console = Console()
    console.print("\n")
    # console.print("[bold magenta]Detailed updates[/bold magenta]")
    
    for address, changes in updates.items():
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Field",  width=50)
        table.add_column("From", justify="left")
        table.add_column("To", justify="left")
        
        for field, change in changes.items():
            # Format the 'from' value
            from_value = change['from']
            if isinstance(from_value, (dict, list)):
                from_value = json.dumps(from_value, indent=2)
            else:
                from_value = str(from_value)

            # Format the 'to' value
            to_value = change['to']
            if isinstance(to_value, (dict, list)):
                to_value = json.dumps(to_value, indent=2)
            else:
                to_value = str(to_value)

            table.add_row(field, from_value, to_value)
        
        console.print(f"Resource [bold cyan]{address}[/bold cyan]:")
        console.print(table)


def print_summary(counts, module):
    console = Console()
    console.print(f"[bold green]{module.upper()} Summary:[/bold green]")
    action_colors = {
        "imported": "green",
        "added": "green",
        "updated": "orange3",
        "destroyed": "red",
        "no-op": "grey"
    }

    for action, count in counts.items():
        if count > 0:
            console.print(f"[{action_colors[action]}]{action.title()}: {count}[/{action_colors[action]}]", end="  ")
    console.print("\n")

# if __name__ == "__main__":
#     with open('s3_plan.json', 'r') as file:
#         terraform_plan = file.read()

#     counts, updates = count_resources_by_action_and_collect_changes(terraform_plan)
    
#     print_summary(counts, "s3")
    
#     print_detailed_changes(updates)