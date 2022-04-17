import inspect
import json
import os


def get_function_name(): return inspect.stack()[1][3]


def dump_json(data, path="tmp.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def load_json(path="tmp.json"):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def print_json(data):
    print(json.dumps(data, indent=2))


def print_items(items):
    count = len(items)
    limit = min(3, count)
    print("Anzahl", count)
    for num, item in enumerate(items[:limit]):
        print(num, json.dumps(item, indent=2))


def get_project_path(user_name):
    document_path = os.path.expanduser('~/Documents')
    project_path = f"{document_path}/instagram-scripts"
    webdriver_path = f"{project_path}/webdriver"
    account_path = f"{project_path}/accounts/{user_name}"

    os.makedirs(project_path, exist_ok=True)
    os.makedirs(webdriver_path, exist_ok=True)
    os.makedirs(account_path, exist_ok=True)

    return {
        "project": project_path,
        "database": f"{account_path}/database.db",
        "web": f"{account_path}/web.cookies",
        "mobile": f"{account_path}/mobile.cookies",
        "selenium": f"{account_path}/selenium.cookies",
    }
