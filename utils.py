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
