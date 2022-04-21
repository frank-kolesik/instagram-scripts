import math
import sre_compile
import datetime
import requests
import pickle
import random
import time
import os
import re


from utils import (
    get_project_path,
    get_function_name,
)


APP_VERSION = "136.0.0.34.124"
VERSION_CODE = "208061712"

USER_AGENT_BASE = (
    "Instagram {app_version} "
    "Android ({android_version}/{android_release}; "
    "{dpi}; {resolution}; {manufacturer}; "
    "{device}; {model}; {cpu}; en_US; {version_code})"
)

USER_AGENT = USER_AGENT_BASE.format(**{
    "app_version": APP_VERSION,
    "android_version": "28",
    "android_release": "9.0",
    "dpi": "640dpi",
    "resolution": "1440x2560",
    "manufacturer": "samsung",
    "device": "SM-G965F",
    "model": "star2qltecs",
    "cpu": "samsungexynos9810",
    "version_code": VERSION_CODE,
})

REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "X-IG-App-Locale": "en_US",
    "X-IG-Device-Locale": "en_US",
    "X-IG-Mapped-Locale": "en_US",
    "X-Pigeon-Session-Id": "d0a3c6b0-24fd-428c-9d20-624a839f7f08",
    "X-Pigeon-Rawclienttime": str(round(time.time() * 1000)),
    "X-IG-Connection-Speed": "-1kbps",
    "X-IG-Bandwidth-Speed-KBPS": str(random.randint(7000, 10000)),
    "X-IG-Bandwidth-TotalBytes-B": str(random.randint(500000, 900000)),
    "X-IG-Bandwidth-TotalTime-MS": str(random.randint(50, 150)),
    "X-IG-App-Startup-Country": "US",
    "X-Bloks-Version-Id": "0a3ae4c88248863609c67e278f34af44673cff300bc76add965a9fb036bd3ca3",
    # X-IG-WWW-Claim: hmac.AR1ETv6FsubYON5DwNj_0CLNmbW7hSNR1yIMeXuhHJORNxSt
    "X-IG-WWW-Claim": "hmac.AR1ETv6FsubYON5DwNj_0CLNmbW7hSNR1yIMeXuhHJORN4n7",
    "X-Bloks-Is-Layout-RTL": "false",
    "X-Bloks-Enable-RenderCore": "false",
    # TODO get the uuid from api_login here
    # "X-IG-Device-ID": "{uuid}",
    # TODO get the device_id from api_login here
    # "X-IG-Android-ID": "{device_id}",
    "X-IG-Connection-Type": "WIFI",
    "X-IG-Capabilities": "3brTvwM=",
    "X-IG-App-ID": "567067343352427",
    "Accept-Language": "en-US",
    # Can be get from a cookie, self.mid
    # "X-MID": "{mid}",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept-Encoding": "gzip, deflate",
    "Host": "i.instagram.com",
    "X-FB-HTTP-Engine": "Liger",
    "Connection": "close",
    "X-IG-Prefetch-Request": "foreground",
}


def manipulate(keys, predicate=None):
    def keys_dict(items):
        result = []

        for item in items:
            if predicate and not predicate(item):
                continue

            layer_1 = {}
            for k, v in keys.items():
                if isinstance(v, dict):
                    if k not in item:
                        continue

                    layer_2 = {}
                    for sub_k, sub_v in v.items():
                        if sub_v not in item[k]:
                            continue

                        layer_2[sub_k] = item[k][sub_v]

                    layer_1.update(layer_2)
                else:
                    if v not in item:
                        continue
                    layer_1[k] = item[v]

            result.append(layer_1)

        return result

    def keys_list(items):
        return [
            {
                k: item[k]
                for k in keys
                if k in item
            } for item in items
            if not predicate or predicate(item)
        ]

    if isinstance(keys, dict):
        return keys_dict

    if isinstance(keys, list):
        return keys_list

    return None


class InstagramArray():

    @staticmethod
    def filter_nodes(items, key="node"):
        return [item[key] for item in items]

    @staticmethod
    def filter_nodes_v2(items):
        result = []
        for item in items:
            if item["layout_type"] != "media_grid" or item["feed_type"] != "media":
                continue
            media = item["layout_content"]["medias"]
            tmp = InstagramArray.filter_nodes(media, "media")
            result.extend(tmp)
        return result

    @staticmethod
    def filter_nodes_activity(items):
        result = []
        for item in items:
            item = item['node']
            typename = re.search(
                r'Graph(.*?)AggregatedStory',
                item['__typename']
            ).group(1)

            tmp = {
                'type': typename,
                'userid': item['user']['id'],
                'username': item['user']['username'],
            }

            if typename != 'Follow':
                tmp['mediaid'] = item['media']['id']
                tmp['shortcode'] = item['media']['shortcode']

            result.append(tmp)
        return result


class InstagramAPI():

    # BASE URLS
    URL_BASE = "https://www.instagram.com/"
    URL_LOGIN = "https://www.instagram.com/accounts/login/ajax/"
    URL_LOGOUT = "https://www.instagram.com/accounts/logout/"
    URL_API = "https://www.instagram.com/graphql/query/?query_hash=%s&%s"
    URL_API_v2 = "https://www.instagram.com/graphql/query/?query_id=%s&%s"

    # DATA URLS
    URL_USER = "https://www.instagram.com/%s/?__a=1"
    URL_MEDIA = "https://www.instagram.com/p/%s/?__a=1"
    URL_TAG = "https://www.instagram.com/explore/tags/%s/?__a=1"
    URL_LOCATION = "https://www.instagram.com/explore/locations/%s/?__a=1"

    URL_ACTIVITY = "https://www.instagram.com/accounts/activity/?__a=1"
    URL_ACCESS_TOOL_BASE = "https://www.instagram.com/accounts/access_tool/%s?__a=1"
    URL_ACCESS_TOOLS = URL_ACCESS_TOOL_BASE % ""
    URL_OUTGOING_FOLLOW_REQUESTS = URL_ACCESS_TOOL_BASE % "current_follow_requests"
    URL_INCOMING_USER_FOLLOWS = URL_ACCESS_TOOL_BASE % "accounts_following_you"
    URL_OUTGOING_USER_FOLLOWS = URL_ACCESS_TOOL_BASE % "accounts_you_follow"
    URL_OUTGOING_TAG_FOLLOWS = URL_ACCESS_TOOL_BASE % "hashtags_you_follow"
    URL_OUTGOING_USER_BLOCKS = URL_ACCESS_TOOL_BASE % "accounts_you_blocked"
    URL_OUTGOING_USER_HIDE_STORY = URL_ACCESS_TOOL_BASE % "accounts_you_hide_stories_from"
    # pagination: &cursor=...

    # ACTION URLS
    URL_LIKE = "https://www.instagram.com/web/likes/%s/like/"
    URL_UNLIKE = "https://www.instagram.com/web/likes/%s/unlike/"
    URL_LIKE_COMMENT = "https://www.instagram.com/web/comments/like/%s/"
    URL_UNLIKE_COMMENT = "https://www.instagram.com/web/comments/unlike/%s/"
    URL_COMMENT = "https://www.instagram.com/web/comments/%s/add/"
    URL_UNCOMMENT = "https://www.instagram.com/web/comments/%s/delete/%s/"
    URL_FOLLOW = "https://www.instagram.com/web/friendships/%s/follow/"
    URL_UNFOLLOW = "https://www.instagram.com/web/friendships/%s/unfollow/"
    URL_APPROVE_FOLLOWER = "https://www.instagram.com/web/friendships/%s/approve/"
    URL_REMOVE_FOLLOWER = "https://www.instagram.com/web/friendships/%s/remove_follower/"
    URL_BLOCK = "https://www.instagram.com/web/friendships/%s/block/"
    URL_UNBLOCK = "https://www.instagram.com/web/friendships/%s/unblock/"
    URL_FOLLOW_TAG = "https://www.instagram.com/web/tags/follow/%s/"
    URL_UNFOLLOW_TAG = "https://www.instagram.com/web/tags/unfollow/%s/"

    # URL_VIEW_STORY = "https://www.instagram.com/stories/reel/seen"
    URL_VIEW_STORY = "https://i.instagram.com/api/v1/stories/reel/seen"

    # VARIABLES
    HEADERS_WEB = {
        "accept": "*/*",
        "accept-language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "accept-encoding": "gzip, deflate, br",
        "content-type": "application/x-www-form-urlencoded",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36",
        "host": "www.instagram.com",
        "origin": "https://www.instagram.com",
        "referrer": "https://www.instagram.com/",
        "x-requested-with": "XMLHttpRequest",
    }

    def __init__(self, config, force_login=False):
        self.username = config.get("username")
        self.password = config.get("password")
        self.userid = config.get("userid")

        self.s = requests.Session()
        self.s.headers.update(self.HEADERS_WEB)

        paths = get_project_path(self.username)
        self.cookies_web = paths.get("web")

        self.login(force_login)

    # LOGIN/LOGOUT
    def login(self, force_login):
        if os.path.exists(self.cookies_web) and not force_login:
            with open(self.cookies_web, 'rb') as f:
                self.s = pickle.load(f)
            return print("Login succeeded (cookies)")

        res = self.s.get("https://www.instagram.com")
        csrf_token = re.search('(?<="csrf_token":")\\w+', res.text).group(0)
        self.s.headers.update({"X-CSRFToken": csrf_token})

        time = int(datetime.datetime.now().timestamp())
        login_data = {
            "username": self.username,
            "enc_password": f"#PWD_INSTAGRAM_BROWSER:0:{time}:{self.password}",
        }

        login = self.s.post(
            self.URL_LOGIN,
            data=login_data,
            allow_redirects=True
        )

        try:
            json_data = login.json()

            cookies = requests.utils.dict_from_cookiejar(login.cookies)
            csrf_token = cookies.get("csrftoken")
            self.s.headers.update({"X-CSRFToken": csrf_token})
            self.s.cookies.update(cookies)

            pk = json_data["userId"]
            with open(self.cookies_web, "wb") as f:
                pickle.dump(self.s, f)
            print("Login succeeded", pk)
        except:
            print("Login failed")

    def logout(self):
        if os.path.exists(self.cookies_web):
            os.remove(self.cookies_web)

        self.s.post(self.URL_LOGOUT)
        print("Logout succeeded")

    # HELPER FUNCTIONS
    def _get_response(self, link):
        try:
            response = self.s.get(link).json()
        except Exception as e:
            print(get_function_name(), link, e)
            return {}
        return response

    def _get_user_id_by_user_name(self, user_name):
        '''
            @param String user_name
            @return String | None
        '''
        response = self._get_response(self.URL_USER % user_name)
        try:
            user_id = response['graphql']['user']['id']
            return user_id
        except Exception as e:
            print(get_function_name(), e)
            return None

    def _get_user_id_by_short_code(self, short_code):
        '''
            @param String short_code
            @return String | None
        '''
        query_hash = '6ff3f5c474a240353993056428fb851e'
        query_vars = 'variables={"shortcode":"%s","include_reel":true}'
        query_vars = query_vars % short_code
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            user_id = response['data']['shortcode_media']['owner']['reel']['owner']['id']
            return user_id
        except Exception as e:
            print(get_function_name(), e)
            return None

    def _get_user_name_by_user_id(self, user_id):
        '''
            @param String user_id
            @return String | None
        '''
        query_hash = 'd4d88dc1500312af6f937f7b804c68c3'
        # c9100bf9110dd6361671f113dd02e7d6
        query_vars = 'variables={"user_id":%s,"include_reel":true}'
        query_vars = query_vars % user_id
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            user_name = response['data']['user']['reel']['owner']['username']
            return user_name
        except Exception as e:
            print(get_function_name(), e)
            return None

    def _get_user_name_by_short_code(self, short_code):
        '''
            @param String short_code
            @return String | None
        '''
        query_hash = '6ff3f5c474a240353993056428fb851e'
        query_vars = 'variables={"shortcode":"%s","include_reel":true}'
        query_vars = query_vars % short_code
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            user_name = response['data']['shortcode_media']['owner']['reel']['owner']['username']
            return user_name
        except Exception as e:
            print(get_function_name(), e)
            return None

    def _get_media_id_by_short_code(self, short_code):
        '''
            @param String short_code
            @return String | None
        '''
        response = self._get_response(self.URL_MEDIA % short_code)
        try:
            media_id = response['items'][0]['id']
            media_id = media_id.split("_")[0]
            return media_id
        except Exception as e:
            print(get_function_name(), e)
            return None

    # DATA FUNCTIONS
    def _get_user_info_by_username(self, user_name):
        '''
            @param String user_name
            @return User | None
        '''
        response = self._get_response(self.URL_USER % user_name)
        try:
            user = response['graphql']['user']
            return {
                "userid": user['id'],
                "username": user['username'],
                "private": user['is_private'],
                "following": user['edge_follow']['count'],
                "followers": user['edge_followed_by']['count'],
                "posts": user['edge_owner_to_timeline_media']['count'],
            }
        except Exception as e:
            print(get_function_name(), e)
            return None

    def _get_user_account_activity(self):
        '''
            @return Activity[]
        '''
        response = self._get_response(self.URL_ACTIVITY)
        try:
            response = response['graphql']['user']['activity_feed']['edge_web_activity_feed']
            edges = response['edges']
            return InstagramArray.filter_nodes_activity(edges)
        except Exception as e:
            print(get_function_name(), e)
            return []

    def _get_incoming_follow_requests(self):
        '''
            @return String[]
        '''
        response = self._get_response(self.URL_ACTIVITY)
        try:
            response = response['graphql']['user']['edge_follow_requests']
            edges = response['edges']
            return InstagramArray.filter_nodes(edges)
        except Exception as e:
            print(get_function_name(), e)
            return []

    def _get_outgoing_follow_requests(self):
        '''
            @return String[]
        '''
        response = self._get_response(self.URL_OUTGOING_FOLLOW_REQUESTS)
        try:
            response = response['data']['data']
            return [item['text'] for item in response]
        except Exception as e:
            print(get_function_name(), e)
            return []

    def _get_user_followings_by_user_id(self, user_id, end_cursor=""):
        '''
            @param String user_id
            @param String end_cursor, optional
            @return [ User[], String | None ]
        '''
        query_hash = 'd04b0a864b4b54837c0d870b0e77e076'
        # 58712303d941c6855d4e888c5f0cd22f
        query_vars = 'variables={"id":"%s","first":50,"after":"%s"}'
        query_vars = query_vars % (user_id, end_cursor)
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            response = response['data']['user']['edge_follow']
            edges = response["edges"]
            cursor = response["page_info"]

            edges = InstagramArray.filter_nodes(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [edges, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_user_followings_by_user_id_v2(self, user_id, end_cursor=""):
        '''
            @param String user_id
            @param String end_cursor, optional
            @return [ User[], String | None ]
        '''
        query_hash = '17874545323001329'
        query_vars = 'id=%s&first=50&after=%s'
        query_vars = query_vars % (user_id, end_cursor)
        response = self._get_response(
            self.URL_API_v2 % (query_hash, query_vars)
        )
        try:
            response = response['data']['user']['edge_follow']
            edges = response["edges"]
            cursor = response["page_info"]

            edges = InstagramArray.filter_nodes(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [edges, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_user_followers_by_user_id(self, user_id, end_cursor=""):
        '''
            @param String user_id
            @param String end_cursor, optional
            @return [ User[], String | None ]
        '''
        query_hash = 'c76146de99bb02f6415203be841dd25a'
        # 37479f2b8209594dde7facb0d904896a
        query_vars = 'variables={"id":"%s","first":50,"after":"%s"}'
        query_vars = query_vars % (user_id, end_cursor)
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            response = response['data']['user']['edge_followed_by']
            edges = response["edges"]
            cursor = response["page_info"]

            edges = InstagramArray.filter_nodes(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [edges, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_user_followers_by_user_id_v2(self, user_id, end_cursor=""):
        '''
            @param String user_id
            @param String end_cursor, optional
            @return [ User[], String | None ]
        '''
        query_hash = '17851374694183129'
        query_vars = 'id=%s&first=50&after=%s'
        query_vars = query_vars % (user_id, end_cursor)
        response = self._get_response(
            self.URL_API_v2 % (query_hash, query_vars)
        )
        try:
            response = response['data']['user']['edge_followed_by']
            edges = response["edges"]
            cursor = response["page_info"]

            edges = InstagramArray.filter_nodes(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [edges, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_media_likes_by_short_code(self, short_code, end_cursor=""):
        '''
            @param String short_code
            @param String end_cursor, optional
            @return [ Like[], String | None ]
        '''
        query_hash = 'd5d763b1e2acf209d62d22d184488e57'
        query_vars = 'variables={"shortcode":"%s","first":50,"after":"%s"}'
        query_vars = query_vars % (short_code, end_cursor)
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            response = response['data']['shortcode_media']['edge_liked_by']
            edges = response["edges"]
            cursor = response["page_info"]

            edges = InstagramArray.filter_nodes(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [edges, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_media_likes_by_short_code_v2(self, short_code, end_cursor=""):
        '''
            @param String short_code
            @param String end_cursor, optional
            @return [ Like[], String | None ]
        '''
        query_hash = '17864450716183058'
        query_vars = 'shortcode=%s&first=50&after=%s'
        query_vars = query_vars % (short_code, end_cursor)
        response = self._get_response(
            self.URL_API_v2 % (query_hash, query_vars)
        )
        try:
            response = response['data']['shortcode_media']['edge_liked_by']
            edges = response["edges"]
            cursor = response["page_info"]

            edges = InstagramArray.filter_nodes(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [edges, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_media_comments_by_short_code(self, short_code, end_cursor=""):
        '''
            @param String short_code
            @param String end_cursor, optional
            @return [ Comment[], String | None ]
        '''
        query_hash = '33ba35852cb50da46f5b5e889df7d159'
        query_vars = 'variables={"shortcode":"%s","first":50,"after":"%s"}'
        query_vars = query_vars % (short_code, end_cursor)
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            response = response['data']['shortcode_media']['edge_media_to_comment']
            edges = response["edges"]
            cursor = response["page_info"]

            edges = InstagramArray.filter_nodes(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [edges, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_media_comments_by_short_code_v2(self, short_code, end_cursor=""):
        '''
            @param String short_code
            @param String end_cursor, optional
            @return [ Comment[], String | None ]
        '''
        query_hash = '17852405266163336'
        query_vars = 'shortcode=%s&first=50&after=%s'
        query_vars = query_vars % (short_code, end_cursor)
        response = self._get_response(
            self.URL_API_v2 % (query_hash, query_vars)
        )
        try:
            response = response['data']['shortcode_media']['edge_media_to_comment']
            edges = response["edges"]
            cursor = response["page_info"]

            edges = InstagramArray.filter_nodes(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [edges, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_timeline(self, end_cursor=""):
        '''
            @param String end_cursor, optional
            @return [ Media[], String | None ]
        '''
        query_hash = '3f01472fb28fb8aca9ad9dbc9d4578ff'
        response = self._get_response(self.URL_API % (query_hash, ""))
        try:
            response = response['data']['user']['edge_web_feed_timeline']
            edges = response["edges"]
            cursor = response["page_info"]

            edges = InstagramArray.filter_nodes(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [edges, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_timeline_v2(self, end_cursor=""):
        '''
            @param String end_cursor, optional
            @return [ Media[], String | None ]
        '''
        query_hash = '17861995474116400'
        query_vars = 'fetch_media_item_count=12&fetch_media_item_cursor=%s'
        query_vars = query_vars % end_cursor
        response = self._get_response(
            self.URL_API_v2 % (query_hash, query_vars)
        )
        try:
            response = response['data']['user']['edge_web_feed_timeline']
            edges = response["edges"]
            cursor = response["page_info"]

            edges = InstagramArray.filter_nodes(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [edges, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_post_suggestions(self, end_cursor=""):
        '''
            @param String end_cursor, optional
            @return [ Media[], String | None ]
        '''
        query_hash = '17863787143139595'
        query_vars = '&first=50&after=%s'
        query_vars = query_vars % end_cursor
        response = self._get_response(
            self.URL_API_v2 % (query_hash, query_vars)
        )
        try:
            response = response['data']['user']['edge_web_discover_media']
            edges = response["edges"]
            cursor = response["page_info"]

            edges = InstagramArray.filter_nodes(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [edges, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_stories(self):
        '''
            @return Story[]
        '''
        query_hash = '04334405dbdef91f2c4e207b84c204d7'
        query_vars = 'variables={"only_stories":true}'
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            response = response["data"]["user"]["feed_reels_tray"]["edge_reels_tray_to_reel"]
            edges = response["edges"]
            return InstagramArray.filter_nodes(edges)
        except Exception as e:
            print(get_function_name(), e)
            return []

    def _get_user_stories(self, user_id):
        '''
            @param String[] | String user_id
            @return Story[]
        '''
        if isinstance(user_id, list):
            user_id = '","'.join(user_id)
        query_hash = 'cda12de4f7fd3719c0569ce03589f4c4'
        query_vars = (
            'variables={"reel_ids":["%s"],"tag_names":[],"location_ids":[],"highlight_reel_ids":[],'
            # '"show_story_viewer_list":true,"story_viewer_fetch_count":50,"story_viewer_cursor":"",'
            '"precomposed_overlay":false}'
        )
        query_vars = query_vars % user_id
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            response = response["data"]
            edges = response["reels_media"]
            return edges
        except Exception as e:
            print(get_function_name(), e)
            return []

    def _get_user_feed_by_user_name(self, user_name):
        '''
            @param String user_name
            @return Media[]
        '''
        response = self._get_response(self.URL_USER % user_name)
        try:
            response = response['graphql']['user']['edge_owner_to_timeline_media']
            edges = response['edges']
            return InstagramArray.filter_nodes(edges)
        except Exception as e:
            print(get_function_name(), e)
            return []

    def _get_user_feed_by_user_id(self, user_id, end_cursor=""):
        '''
            @param String user_id
            @param String end_cursor, optional
            @return [ Media[], String | None ]
        '''
        query_hash = 'e7e2f4da4b02303f74f0841279e52d76'
        # 003056d32c2554def87228bc3fd9668a
        # e769aa130647d2354c40ea6a439bfc08
        # 8c2a529969ee035a5063f2fc8602a0fd
        # 396983faee97f4b49ccbe105b4daf7a0
        # 42323d64886122307be10013ad2dcc44
        # 472f257a40c653c64c666ce877d59d2b
        query_vars = 'variables={"id":%s,"first":50,"after":"%s"}'
        query_vars = query_vars % (user_id, end_cursor)
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            response = response['data']['user']['edge_owner_to_timeline_media']
            edges = response["edges"]
            cursor = response["page_info"]

            edges = InstagramArray.filter_nodes(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [edges, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_user_feed_by_user_id_v2(self, user_id, end_cursor=""):
        '''
            @param String user_id
            @param String end_cursor, optional
            @return [ Media[], String | None ]
        '''
        query_hash = '17880160963012870'
        # 17888483320059182
        query_vars = 'id=%s&first=50&after=%s'
        query_vars = query_vars % (user_id, end_cursor)
        response = self._get_response(
            self.URL_API_v2 % (query_hash, query_vars)
        )
        try:
            response = response['data']['user']['edge_owner_to_timeline_media']
            edges = response["edges"]
            cursor = response["page_info"]

            edges = InstagramArray.filter_nodes(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [edges, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_user_tagged_feed_by_user_id(self, user_id, end_cursor=""):
        '''
            @param String user_id
            @param String end_cursor, optional
            @return [ Media[], String | None ]
        '''
        query_hash = 'be13233562af2d229b008d2976b998b5'
        query_vars = 'variables={"id":"%s","first":50,"after":"%s"}'
        query_vars = query_vars % (user_id, end_cursor)
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            response = response['data']['user']['edge_user_to_photos_of_you']
            edges = response["edges"]
            cursor = response["page_info"]

            edges = InstagramArray.filter_nodes(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [edges, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_top_hashtag_feed_by_tag_name(self, tag_name):
        '''
            @param String tag_name
            @return Media[]
        '''
        query_hash = 'f92f56d47dc7a55b606908374b43a314'
        query_vars = 'variables={"tag_name":"%s","first":50}'
        query_vars = query_vars % tag_name
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            response = response["data"]["hashtag"]["edge_hashtag_to_top_posts"]
            edges = response["edges"]
            return InstagramArray.filter_nodes(edges)
        except Exception as e:
            print(get_function_name(), e)
            return []

    def _get_top_hashtag_feed_by_tag_name_v2(self, tag_name):
        '''
            @param String tag_name
            @return Media[]
        '''
        query_hash = '17875800862117404'
        query_vars = 'tag_name=%s&first=50'
        query_vars = query_vars % tag_name
        response = self._get_response(
            self.URL_API_v2 % (query_hash, query_vars)
        )
        try:
            response = response['data']['hashtag']['edge_hashtag_to_top_posts']
            edges = response["edges"]
            return InstagramArray.filter_nodes(edges)
        except Exception as e:
            print(get_function_name(), e)
            return []

    def _get_top_hashtag_feed_by_tag_name_v3(self, tag_name):
        '''
            @param String tag_name
            @return Media[]
        '''
        response = self._get_response(self.URL_TAG % tag_name)
        try:
            edges = response["data"]["top"]["sections"]
            return InstagramArray.filter_nodes_v2(edges)
        except Exception as e:
            print(get_function_name(), e)
            return []

    def _get_ranked_hashtag_feed_by_tag_name(self, tag_name, end_cursor=""):
        '''
            @param String tag_name
            @param String end_cursor, optional
            @return [ Media[], String | None ]
        '''
        query_hash = 'f92f56d47dc7a55b606908374b43a314'
        query_vars = 'variables={"tag_name":"%s","first":50,"show_ranked":true,"after":"%s"}'
        query_vars = query_vars % (tag_name, end_cursor)
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            response = response["data"]["hashtag"]["edge_hashtag_to_ranked_media"]
            edges = response["edges"]
            cursor = response["page_info"]

            edges = InstagramArray.filter_nodes(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [edges, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_recent_hashtag_feed_by_tag_name(self, tag_name, end_cursor=""):
        '''
            @param String tag_name
            @param String end_cursor, optional
            @return [ Media[], String | None ]
        '''
        query_hash = 'f92f56d47dc7a55b606908374b43a314'
        query_vars = 'variables={"tag_name":"%s","first":50,"after":"%s"}'
        query_vars = query_vars % (tag_name, end_cursor)
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            response = response["data"]["hashtag"]["edge_hashtag_to_media"]
            edges = response["edges"]
            cursor = response["page_info"]

            edges = InstagramArray.filter_nodes(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [edges, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_recent_hashtag_feed_by_tag_name_v2(self, tag_name, end_cursor=""):
        '''
            @param String tag_name
            @param String end_cursor, optional
            @return [ Media[], String | None ]
        '''
        query_hash = '17875800862117404'
        query_vars = 'tag_name=%s&first=50&after=%s'
        query_vars = query_vars % (tag_name, end_cursor)
        response = self._get_response(
            self.URL_API_v2 % (query_hash, query_vars)
        )
        try:
            response = response['data']['hashtag']['edge_hashtag_to_media']
            edges = response["edges"]
            cursor = response["page_info"]

            edges = InstagramArray.filter_nodes(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [edges, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_recent_hashtag_feed_by_tag_name_v3(self, tag_name):
        '''
            @param String tag_name
            @return Media[]
        '''
        response = self._get_response(self.URL_TAG % tag_name)
        try:
            edges = response["data"]["recent"]["sections"]
            return InstagramArray.filter_nodes_v2(edges)
        except Exception as e:
            print(get_function_name(), e)
            return []

    def _get_ranked_location_feed_by_location_id(self, location_id):
        '''
            @param String location_id
            @return Media[]
        '''
        response = self._get_response(self.URL_LOCATION % location_id)
        try:
            edges = response["native_location_data"]["ranked"]["sections"]
            return InstagramArray.filter_nodes_v2(edges)
        except Exception as e:
            print(get_function_name(), e)
            return []

    def _get_recent_location_feed_by_location_id(self, location_id):
        '''
            @param String location_id
            @return Media[]
        '''
        response = self._get_response(self.URL_LOCATION % location_id)
        try:
            edges = response["native_location_data"]["recent"]["sections"]
            return InstagramArray.filter_nodes_v2(edges)
        except Exception as e:
            print(get_function_name(), e)
            return []

    # USER DATA
    def get_user_id(self, user_name=None, short_code=None):
        '''
            @param String user_name
            @param String short_code
            @return String | None
        '''
        user_id = None
        if user_name:
            user_id = self._get_user_id_by_user_name(user_name)
        if not user_id and short_code:
            user_id = self._get_user_id_by_short_code(short_code)
        print(f'[{get_function_name()}] returning user_id: {user_id}')
        return user_id

    def get_user_name(self, user_id=None, short_code=None):
        '''
            @param String user_id
            @param String short_code
            @return String | None
        '''
        user_name = None
        if user_id:
            user_name = self._get_user_name_by_user_id(user_id)
        if not user_name and short_code:
            user_name = self._get_user_name_by_short_code(short_code)
        print(f'[{get_function_name()}] returning user_name: {user_name}')
        return user_name

    # USER INFO
    def get_user_info(self, user_name):
        '''
            @param String user_name
            @return User | None
        '''
        print(f'[{get_function_name()}] returning user_info: {user_name}')
        return self._get_user_info_by_username(user_name)

    def get_self_user_info(self):
        '''
            @return User | None
        '''
        return self.get_user_info(self.username)

    # USER FOLLOWINGS
    def get_user_followings(self, user_id, limit=float('inf'), manipulate=None):
        '''
            @param String user_id
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return User[]
        '''
        [items, end_cursor] = self._get_user_followings_by_user_id(user_id)

        if manipulate:
            items = manipulate(items)

        number = len(items)
        while end_cursor and number < limit:
            print(f'[{get_function_name()}] fetching users: {number}', end='\r')

            time.sleep(random.randint(1, 2))

            [items_new, end_cursor] = self._get_user_followings_by_user_id(
                user_id, end_cursor
            )

            if manipulate:
                items_new = manipulate(items_new)

            items.extend(items_new)
            number = len(items)

        number = min(limit, number)
        print(f'[{get_function_name()}] returning users: {number}')
        return items[:number]

    def get_self_user_followings(self, limit=float('inf'), manipulate=None):
        '''
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return User[]
        '''
        return self.get_user_followings(
            user_id=self.userid,
            limit=limit,
            manipulate=manipulate,
        )

    def get_user_followings_v2(self, user_id, limit=float('inf'), manipulate=None):
        '''
            @param String user_id
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return User[]
        '''
        [items, end_cursor] = self._get_user_followings_by_user_id_v2(user_id)

        if manipulate:
            items = manipulate(items)

        number = len(items)
        while end_cursor and number < limit:
            print(f'[{get_function_name()}] fetching users: {number}', end='\r')

            time.sleep(random.randint(1, 2))

            [items_new, end_cursor] = self._get_user_followings_by_user_id_v2(
                user_id, end_cursor
            )

            if manipulate:
                items_new = manipulate(items_new)

            items.extend(items_new)
            number = len(items)

        number = min(limit, number)
        print(f'[{get_function_name()}] returning users: {number}')
        return items[:number]

    def get_self_user_followings_v2(self, limit=float('inf'), manipulate=None):
        '''
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return User[]
        '''
        return self.get_user_followings_v2(
            user_id=self.userid,
            limit=limit,
            manipulate=manipulate,
        )

    # USER FOLLOWERS
    def get_user_followers(self, user_id, limit=float('inf'), manipulate=None):
        '''
            @param String user_id
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return User[]
        '''
        [items, end_cursor] = self._get_user_followers_by_user_id(user_id)

        if manipulate:
            items = manipulate(items)

        number = len(items)
        while end_cursor and number < limit:
            print(f'[{get_function_name()}] fetching users: {number}', end='\r')

            time.sleep(random.randint(1, 2))

            [items_new, end_cursor] = self._get_user_followers_by_user_id(
                user_id, end_cursor
            )

            if manipulate:
                items_new = manipulate(items_new)

            items.extend(items_new)
            number = len(items)

        number = min(limit, number)
        print(f'[{get_function_name()}] returning users: {number}')
        return items[:number]

    def get_self_user_followers(self, limit=float('inf'), manipulate=None):
        '''
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return User[]
        '''
        return self.get_user_followers(
            user_id=self.userid,
            limit=limit,
            manipulate=manipulate,
        )

    def get_user_followers_v2(self, user_id, limit=float('inf'), manipulate=None):
        '''
            @param String user_id
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return User[]
        '''
        [items, end_cursor] = self._get_user_followers_by_user_id_v2(user_id)

        if manipulate:
            items = manipulate(items)

        number = len(items)
        while end_cursor and number < limit:
            print(f'[{get_function_name()}] fetching users: {number}', end='\r')

            time.sleep(random.randint(1, 2))

            [items_new, end_cursor] = self._get_user_followers_by_user_id_v2(
                user_id, end_cursor
            )

            if manipulate:
                items_new = manipulate(items_new)

            items.extend(items_new)
            number = len(items)

        number = min(limit, number)
        print(f'[{get_function_name()}] returning users: {number}')
        return items[:number]

    def get_self_user_followers_v2(self, limit=float('inf'), manipulate=None):
        '''
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return User[]
        '''
        return self.get_user_followers_v2(
            user_id=self.userid,
            limit=limit,
            manipulate=manipulate,
        )

    # MEDIA LIKES
    def get_media_likes(self, short_code, limit=float('inf'), manipulate=None):
        '''
            @param String short_code
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Like[]
        '''
        [items, end_cursor] = self._get_media_likes_by_short_code(short_code)

        if manipulate:
            items = manipulate(items)

        number = len(items)
        while end_cursor and number < limit:
            print(f'[{get_function_name()}] fetching likes: {number}', end='\r')

            time.sleep(random.randint(1, 2))

            [items_new, end_cursor] = self._get_media_likes_by_short_code(
                short_code, end_cursor
            )

            if manipulate:
                items_new = manipulate(items_new)

            items.extend(items_new)
            number = len(items)

        number = min(limit, number)
        print(f'[{get_function_name()}] returning likes: {number}')
        return items[:number]

    def get_media_likes_v2(self, short_code, limit=float('inf'), manipulate=None):
        '''
            @param String short_code
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Like[]
        '''
        [items, end_cursor] = self._get_media_likes_by_short_code_v2(
            short_code
        )

        if manipulate:
            items = manipulate(items)

        number = len(items)
        while end_cursor and number < limit:
            print(f'[{get_function_name()}] fetching likes: {number}', end='\r')

            time.sleep(random.randint(1, 2))

            [items_new, end_cursor] = self._get_media_likes_by_short_code_v2(
                short_code, end_cursor
            )

            if manipulate:
                items_new = manipulate(items_new)

            items.extend(items_new)
            number = len(items)

        number = min(limit, number)
        print(f'[{get_function_name()}] returning likes: {number}')
        return items[:number]

    # MEDIA COMMENTS
    def get_media_comments(self, short_code, limit=float('inf'), manipulate=None):
        '''
            @param String short_code
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Comment[]
        '''
        [items, end_cursor] = self._get_media_comments_by_short_code(
            short_code
        )

        if manipulate:
            items = manipulate(items)

        number = len(items)
        while end_cursor and number < limit:
            print(f'[{get_function_name()}] fetching comments: {number}', end='\r')

            time.sleep(random.randint(1, 2))

            [items_new, end_cursor] = self._get_media_comments_by_short_code(
                short_code, end_cursor
            )

            if manipulate:
                items_new = manipulate(items_new)

            items.extend(items_new)
            number = len(items)

        number = min(limit, number)
        print(f'[{get_function_name()}] returning comments: {number}')
        return items[:number]

    def get_media_comments_v2(self, short_code, limit=float('inf'), manipulate=None):
        '''
            @param String short_code
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Comment[]
        '''
        [items, end_cursor] = self._get_media_comments_by_short_code_v2(
            short_code
        )

        if manipulate:
            items = manipulate(items)

        number = len(items)
        while end_cursor and number < limit:
            print(f'[{get_function_name()}] fetching comments: {number}', end='\r')

            time.sleep(random.randint(1, 2))

            [items_new, end_cursor] = self._get_media_comments_by_short_code_v2(
                short_code, end_cursor
            )

            if manipulate:
                items_new = manipulate(items_new)

            items.extend(items_new)
            number = len(items)

        number = min(limit, number)
        print(f'[{get_function_name()}] returning comments: {number}')
        return items[:number]

    # TIMELINE FEED
    def get_timeline(self, limit=float('inf'), manipulate=None):
        '''
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        [items, end_cursor] = self._get_timeline()

        if manipulate:
            items = manipulate(items)

        number = len(items)
        while end_cursor and number < limit:
            print(f'[{get_function_name()}] fetching medias: {number}', end='\r')

            time.sleep(random.randint(1, 2))

            [items_new, end_cursor] = self._get_timeline(end_cursor)

            if manipulate:
                items_new = manipulate(items_new)

            items.extend(items_new)
            number = len(items)

        number = min(limit, number)
        print(f'[{get_function_name()}] returning medias: {number}')
        return items[:number]

    def get_timeline_v2(self, limit=float('inf'), manipulate=None):
        '''
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        [items, end_cursor] = self._get_timeline_v2()

        if manipulate:
            items = manipulate(items)

        number = len(items)
        while end_cursor and number < limit:
            print(f'[{get_function_name()}] fetching medias: {number}', end='\r')

            time.sleep(random.randint(1, 2))

            [items_new, end_cursor] = self._get_timeline_v2(end_cursor)

            if manipulate:
                items_new = manipulate(items_new)

            items.extend(items_new)
            number = len(items)

        number = min(limit, number)
        print(f'[{get_function_name()}] returning medias: {number}')
        return items[:number]

    def get_post_suggestions(self, limit=float('inf'), manipulate=None):
        '''
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        [items, end_cursor] = self._get_post_suggestions()

        if manipulate:
            items = manipulate(items)

        number = len(items)
        while end_cursor and number < limit:
            print(f'[{get_function_name()}] fetching medias: {number}', end='\r')

            time.sleep(random.randint(1, 2))

            [items_new, end_cursor] = self._get_post_suggestions(end_cursor)

            if manipulate:
                items_new = manipulate(items_new)

            items.extend(items_new)
            number = len(items)

        number = min(limit, number)
        print(f'[{get_function_name()}] returning medias: {number}')
        return items[:number]

    # USER FEED
    def get_user_feed(self, user_id, limit=float('inf'), manipulate=None):
        '''
            @param String user_id
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        [items, end_cursor] = self._get_user_feed_by_user_id(user_id)

        if manipulate:
            items = manipulate(items)

        number = len(items)
        while end_cursor and number < limit:
            print(f'[{get_function_name()}] fetching medias: {number}', end='\r')

            time.sleep(random.randint(1, 2))

            [items, end_cursor] = self._get_user_feed_by_user_id(
                user_id, end_cursor
            )

            if manipulate:
                items_new = manipulate(items_new)

            items.extend(items_new)
            number = len(items)

        number = min(limit, number)
        print(f'[{get_function_name()}] returning medias: {number}')
        return items[:number]

    def get_self_user_feed(self, limit=float('inf'), manipulate=None):
        '''
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        return self.get_user_feed(
            user_id=self.userid,
            limit=limit,
            manipulate=manipulate,
        )

    def get_user_feed_v2(self, user_id, limit=float('inf'), manipulate=None):
        '''
            @param String user_id
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        [items, end_cursor] = self._get_user_feed_by_user_id_v2(user_id)

        if manipulate:
            items = manipulate(items)

        number = len(items)
        while end_cursor and number < limit:
            print(f'[{get_function_name()}] fetching medias: {number}', end='\r')

            time.sleep(random.randint(1, 2))

            [items, end_cursor] = self._get_user_feed_by_user_id_v2(
                user_id, end_cursor
            )

            if manipulate:
                items_new = manipulate(items_new)

            items.extend(items_new)
            number = len(items)

        number = min(limit, number)
        print(f'[{get_function_name()}] returning medias: {number}')
        return items[:number]

    def get_self_user_feed_v2(self, limit=float('inf'), manipulate=None):
        '''
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        return self.get_user_feed_v2(
            user_id=self.userid,
            limit=limit,
            manipulate=manipulate,
        )

    def get_user_feed_v3(self, user_name, limit=float('inf'), manipulate=None):
        '''
            @param String user_name
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        items = self._get_user_feed_by_user_name(user_name)

        if manipulate:
            items = manipulate(items)

        number = min(limit, len(items))
        print(f'[{get_function_name()}] returning medias: {number}')
        return items[:number]

    def get_self_user_feed_v3(self, limit=float('inf'), manipulate=None):
        '''
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        return self.get_user_feed_v3(
            user_name=self.username,
            limit=limit,
            manipulate=manipulate,
        )

    # TAGGED FEED
    def get_user_tagged_feed(self, user_id, limit=float('inf'), manipulate=None):
        '''
            @param String user_id
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        [items, end_cursor] = self._get_user_tagged_feed_by_user_id(user_id)

        if manipulate:
            items = manipulate(items)

        number = len(items)
        while end_cursor and number < limit:
            print(f'[{get_function_name()}] fetching medias: {number}', end='\r')

            time.sleep(random.randint(1, 2))

            [items, end_cursor] = self._get_user_tagged_feed_by_user_id(
                user_id, end_cursor
            )

            if manipulate:
                items_new = manipulate(items_new)

            items.extend(items_new)
            number = len(items)

        number = min(limit, number)
        print(f'[{get_function_name()}] returning medias: {number}')
        return items[:number]

    def get_self_user_tagged_feed(self, limit=float('inf'), manipulate=None):
        '''
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        return self.get_user_tagged_feed(
            user_id=self.userid,
            limit=limit,
            manipulate=manipulate,
        )

    # HASHTAG FEED
    def get_top_hashtag_feed(self, tag_name, limit=float('inf'), manipulate=None):
        '''
            @param String tag_name
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        items = self._get_top_hashtag_feed_by_tag_name(tag_name)

        if manipulate:
            items = manipulate(items)

        number = min(limit, len(items))
        print(f'[{get_function_name()}] returning medias: {number}')
        return items[:number]

    def get_top_hashtag_feed_v2(self, tag_name, limit=float('inf'), manipulate=None):
        '''
            @param String tag_name
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        items = self._get_top_hashtag_feed_by_tag_name_v2(tag_name)

        if manipulate:
            items = manipulate(items)

        number = min(limit, len(items))
        print(f'[{get_function_name()}] returning medias: {number}')
        return items[:number]

    def get_top_hashtag_feed_v3(self, tag_name, limit=float('inf'), manipulate=None):
        '''
            @param String tag_name
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        items = self._get_top_hashtag_feed_by_tag_name_v3(tag_name)

        if manipulate:
            items = manipulate(items)

        number = min(limit, len(items))
        print(f'[{get_function_name()}] returning medias: {number}')
        return items[:number]

    def get_ranked_hashtag_feed(self, tag_name, limit=float('inf'), manipulate=None):
        '''
            @param String tag_name
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        [items, end_cursor] = self._get_ranked_hashtag_feed_by_tag_name(
            tag_name
        )

        if manipulate:
            items = manipulate(items)

        number = len(items)
        while end_cursor and number < limit:
            print(f'[{get_function_name()}] fetching medias: {number}', end='\r')

            time.sleep(random.randint(1, 2))

            [items, end_cursor] = self._get_ranked_hashtag_feed_by_tag_name(
                tag_name, end_cursor
            )

            if manipulate:
                items_new = manipulate(items_new)

            items.extend(items_new)
            number = len(items)

        number = min(limit, number)
        print(f'[{get_function_name()}] returning medias: {number}')
        return items[:number]

    def get_recent_hashtag_feed(self, tag_name, limit=float('inf'), manipulate=None):
        '''
            @param String tag_name
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        [items, end_cursor] = self._get_recent_hashtag_feed_by_tag_name(
            tag_name
        )

        if manipulate:
            items = manipulate(items)

        number = len(items)
        while end_cursor and number < limit:
            print(f'[{get_function_name()}] fetching medias: {number}', end='\r')

            time.sleep(random.randint(1, 2))

            [items, end_cursor] = self._get_recent_hashtag_feed_by_tag_name(
                tag_name, end_cursor
            )

            if manipulate:
                items_new = manipulate(items_new)

            items.extend(items_new)
            number = len(items)

        number = min(limit, number)
        print(f'[{get_function_name()}] returning medias: {number}')
        return items[:number]

    def get_recent_hashtag_feed_v2(self, tag_name, limit=float('inf'), manipulate=None):
        '''
            @param String tag_name
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        [items, end_cursor] = self._get_recent_hashtag_feed_by_tag_name_v2(
            tag_name
        )

        if manipulate:
            items = manipulate(items)

        number = len(items)
        while end_cursor and number < limit:
            print(f'[{get_function_name()}] fetching medias: {number}', end='\r')

            time.sleep(random.randint(1, 2))

            [items, end_cursor] = self._get_recent_hashtag_feed_by_tag_name_v2(
                tag_name, end_cursor
            )

            if manipulate:
                items_new = manipulate(items_new)

            items.extend(items_new)
            number = len(items)

        number = min(limit, number)
        print(f'[{get_function_name()}] returning medias: {number}')
        return items[:number]

    def get_recent_hashtag_feed_v3(self, tag_name, limit=float('inf'), manipulate=None):
        '''
            @param String tag_name
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        items = self._get_recent_hashtag_feed_by_tag_name_v3(tag_name)

        if manipulate:
            items = manipulate(items)

        number = min(limit, len(items))
        print(f'[{get_function_name()}] returning medias: {number}')
        return items[:number]

    # LOCATION FEED
    def get_ranked_location_feed(self, location_id, limit=float('inf'), manipulate=None):
        '''
            @param String location_id
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        items = self._get_ranked_location_feed_by_location_id(location_id)

        if manipulate:
            items = manipulate(items)

        number = min(limit, len(items))
        print(f'[{get_function_name()}] returning medias: {number}')
        return items[:number]

    def get_recent_location_feed(self, location_id, limit=float('inf'), manipulate=None):
        '''
            @param String location_id
            @param Integer limit, optional
            :maximum number of items to retrieve
            @param Function manipulate, optional
            :function to manipulate items
            @return Media[]
        '''
        items = self._get_recent_location_feed_by_location_id(location_id)

        if manipulate:
            items = manipulate(items)

        number = min(limit, len(items))
        print(f'[{get_function_name()}] returning medias: {number}')
        return items[:number]

    # TAKE ACTIONS
    def like_media(self, media_id):
        '''
            @param String media_id
            @return Boolean success
        '''
        res = self.s.post(self.URL_LIKE % media_id)
        return res.status_code == 200

    def unlike_media(self, media_id):
        '''
            @param String media_id
            @return Boolean success
        '''
        res = self.s.post(self.URL_UNLIKE % media_id)
        return res.status_code == 200

    def like_comment(self, comment_id):
        '''
            @param String comment_id
            @return Boolean success
        '''
        res = self.s.post(self.URL_LIKE_COMMENT % comment_id)
        return res.status_code == 200

    def unlike_comment(self, comment_id):
        '''
            @param String comment_id
            @return Boolean success
        '''
        res = self.s.post(self.URL_UNLIKE_COMMENT % comment_id)
        return res.status_code == 200

    def comment_media(self, text, media_id, replied_to_comment_id=None):
        '''
            @param String text
            @param String media_id
            @param String replied_to_comment_id
            @return Boolean success
        '''
        data = {
            'comment_text': text,
            'replied_to_comment_id': replied_to_comment_id,
        }
        res = self.s.post(self.URL_COMMENT % media_id, data=data)
        return res.status_code == 200

    def uncomment_media(self, media_id, comment_id):
        '''
            @param String media_id
            @param String comment_id
            @return Boolean success
        '''
        res = self.s.post(self.URL_UNCOMMENT % (media_id, comment_id))
        return res.status_code == 200

    def follow_user(self, user_id):
        '''
            @param String user_id
            @return Boolean success
        '''
        res = self.s.post(self.URL_FOLLOW % user_id)
        return res.status_code == 200

    def unfollow_user(self, user_id):
        '''
            @param String user_id
            @return Boolean success
        '''
        res = self.s.post(self.URL_UNFOLLOW % user_id)
        return res.status_code == 200

    def approve_follower(self, user_id):
        '''
            @param String user_id
            @return Boolean success
        '''
        res = self.s.post(self.URL_APPROVE_FOLLOWER % user_id)
        return res.status_code == 200

    def remove_follower(self, user_id):
        '''
            @param String user_id
            @return Boolean success
        '''
        res = self.s.post(self.URL_REMOVE_FOLLOWER % user_id)
        return res.status_code == 200

    def block_user(self, user_id):
        '''
            @param String user_id
            @return Boolean success
        '''
        res = self.s.post(self.URL_BLOCK % user_id)
        return res.status_code == 200

    def unblock_user(self, user_id):
        '''
            @param String user_id
            @return Boolean success
        '''
        res = self.s.post(self.URL_UNBLOCK % user_id)
        return res.status_code == 200

    def follow_tag(self, tag_name):
        '''
            @param String tag_name
            @return Boolean success
        '''
        res = self.s.post(self.URL_FOLLOW_TAG % tag_name)
        return res.status_code == 200

    def unfollow_tag(self, tag_name):
        '''
            @param String tag_name
            @return Boolean success
        '''
        res = self.s.post(self.URL_UNFOLLOW_TAG % tag_name)
        return res.status_code == 200

    def view_story(self, media_id, user_id, taken_at_timestamp):
        '''
            @param String media_id
            @param String user_id
            @param Integer taken_at_timestamp
            @return Boolean success
        '''
        data = {
            "reelMediaId": media_id,
            "reelMediaOwnerId": user_id,
            "reelId": user_id,
            "reelMediaTakenAt": taken_at_timestamp,
            "viewSeenAt": taken_at_timestamp,
        }
        res = self.s.post(
            self.URL_VIEW_STORY,
            data=data,
            headers=REQUEST_HEADERS
        )
        return res.status_code == 200

    # DATA ANALYSIS
    def grab_user_nonfollowers(self, user_id):
        '''
            @param String user_id
            @return User[]
        '''
        manipulate_user = manipulate({
            'userid': 'id',
            'username': 'username',
        })

        all_following = self.get_user_followings(
            user_id=user_id,
            manipulate=manipulate_user
        )
        all_followers = self.get_user_followers(
            user_id=user_id,
            manipulate=manipulate_user
        )

        nonfollowers = [
            user for user in all_following if user not in all_followers
        ]

        return nonfollowers

    def grab_self_user_nonfollowers(self):
        '''
            @return User[]
        '''
        return self.grab_user_nonfollowers(self.userid)

    def grab_user_fans(self, user_id):
        '''
            @param String user_id
            @return User[]
        '''
        manipulate_user = manipulate({
            'userid': 'id',
            'username': 'username',
        })

        all_following = self.get_user_followings(
            user_id=user_id,
            manipulate=manipulate_user
        )
        all_followers = self.get_user_followers(
            user_id=user_id,
            manipulate=manipulate_user
        )

        fans = [
            user for user in all_followers if user not in all_following
        ]

        return fans

    def grab_self_user_fans(self):
        '''
            @return User[]
        '''
        return self.grab_user_fans(self.userid)

    def grab_user_mutual_following(self, user_id):
        '''
            @param String user_id
            @return User[]
        '''
        manipulate_user = manipulate({
            'userid': 'id',
            'username': 'username',
        })

        all_following = self.get_user_followings(
            user_id=user_id,
            manipulate=manipulate_user
        )
        all_followers = self.get_user_followers(
            user_id=user_id,
            manipulate=manipulate_user
        )

        fans = [
            user for user in all_followers if user in all_following
        ]

        return fans

    def grab_self_user_mutual_following(self):
        '''
            @return User[]
        '''
        return self.grab_user_mutual_following(self.userid)

    def grab_user_hashtags(self, user_id, limit=float('inf')):
        '''
            @param String user_id
            @param Integer limit, optional
            :maximum number of posts to analyse
            @return String[]
        '''
        manipulate_item = manipulate({
            'edge_media_to_caption': {
                'caption': 'edges',
            },
        })

        items = self.get_user_feed(
            user_id=user_id,
            limit=limit,
            manipulate=manipulate_item
        )
        items = items[:min(limit, len(items))]

        items = [
            item["caption"][0]["node"]["text"]
            for item in items if item["caption"]
        ]

        hashtags = {}
        for item in items:
            tags = set(sre_compile.compile(r"#\w*").findall(item))
            for tag in tags:
                if tag not in hashtags:
                    hashtags[tag] = 0
                hashtags[tag] += 1

        return sorted(hashtags.items(), key=lambda x: x[1], reverse=True)

    def grab_self_user_hashtags(self, limit=float('inf')):
        '''
            @param Integer limit, optional
            :maximum number of posts to analyse
            @return String[]
        '''
        return self.grab_user_hashtags(self.userid, limit)

    def grab_user_hashtags_v2(self, user_id, limit=float('inf')):
        '''
            @param String user_id
            @param Integer limit, optional
            :maximum number of posts to analyse
            @return String[]
        '''
        manipulate_item = manipulate({
            'edge_media_to_caption': {
                'caption': 'edges',
            },
        })

        items = self.get_user_feed_v2(
            user_id=user_id,
            limit=limit,
            manipulate=manipulate_item
        )
        items = items[:min(limit, len(items))]

        items = [
            item["caption"][0]["node"]["text"]
            for item in items if item["caption"]
        ]

        hashtags = {}
        for item in items:
            tags = set(sre_compile.compile(r"#\w*").findall(item))
            for tag in tags:
                if tag not in hashtags:
                    hashtags[tag] = 0
                hashtags[tag] += 1

        return sorted(hashtags.items(), key=lambda x: x[1], reverse=True)

    def grab_self_user_hashtags_v2(self, limit=float('inf')):
        '''
            @param Integer limit, optional
            :maximum number of posts to analyse
            @return String[]
        '''
        return self.grab_user_hashtags_v2(self.userid, limit)

    def grab_user_hashtags_v3(self, user_name, limit=float('inf')):
        '''
            @param String user_name
            @param Integer limit, optional
            :maximum number of posts to analyse
            @return String[]
        '''
        manipulate_item = manipulate({
            'edge_media_to_caption': {
                'caption': 'edges',
            },
        })

        items = self.get_user_feed_v3(
            user_name=user_name,
            limit=limit,
            manipulate=manipulate_item
        )
        items = items[:min(limit, len(items))]

        items = [
            item["caption"][0]["node"]["text"]
            for item in items if item["caption"]
        ]

        hashtags = {}
        for item in items:
            tags = set(sre_compile.compile(r"#\w*").findall(item))
            for tag in tags:
                if tag not in hashtags:
                    hashtags[tag] = 0
                hashtags[tag] += 1

        return sorted(hashtags.items(), key=lambda x: x[1], reverse=True)

    def grab_self_user_hashtags_v3(self, limit=float('inf')):
        '''
            @param Integer limit, optional
            :maximum number of posts to analyse
            @return String[]
        '''
        return self.grab_user_hashtags_v3(self.username, limit)
