import time
import os
import inspect
import json


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
    limit = min(12, count)
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


def filter_user_info(edges, check_private):
    return [
        {
            'userid': edge['node']['id'],
            'username': edge['node']['username']
        } for edge in edges
        if not (check_private and edge['node']['is_private'])
    ]


def filter_user_feed(edges, filter_not_liked=False):
    return [
        {
            "shortcode": edge["node"]["shortcode"],
            "mediaid": edge["node"]["id"],
        } for edge in edges
        if filter_not_liked
        and not edge["node"]["viewer_has_liked"]
    ]


def filter_hashtag_feed(edges):
    media_info = []
    for edge in edges:
        if edge["layout_type"] != "media_grid" or edge["feed_type"] != "media":
            continue

        medias = edge["layout_content"]["medias"]
        medias = [
            {
                "userid": str(media["media"]["user"]["pk"]),
                "mediaid": media["media"]["pk"],
                "shortcode": media["media"]["code"],
                "likes": media["media"]["like_count"],
                "comments": media["media"]["comment_count"],
            } for media in medias
        ]
        media_info.extend(medias)

    return media_info


def filter_hashtag_feed_v2(edges):
    return [
        {
            "userid": edge["node"]["owner"]["id"],
            "mediaid": edge["node"]["id"],
            "shortcode": edge["node"]["shortcode"],
            "likes": edge["node"]["edge_liked_by"]["count"],
            "comments": edge["node"]["edge_media_to_comment"]["count"],
        } for edge in edges
    ]


def progressBar(iterable, prefix='', suffix='', decimals=1, length=100, fill='█', printEnd="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iterable    - Required  : iterable object (Iterable)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    total = len(iterable)

    def printProgressBar(iteration):
        percent = ("{0:." + str(decimals) + "f}").format(
            100 * (iteration / float(total))
        )
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=printEnd)
    printProgressBar(0)
    for i, item in enumerate(iterable):
        yield item
        printProgressBar(i + 1)
    print()


# items = list(range(30))
# for item in progressBar(
#     items,
#     prefix='Progress:',
#     suffix='Complete',
#     length=50
# ):
#     time.sleep(0.1)
