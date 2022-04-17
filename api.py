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


class InstagramArray():

    @staticmethod
    def filter_nodes(items):
        return [item["node"] for item in items]

    @staticmethod
    def filter_nodes_v2(items):
        result = []
        for item in items:
            if item["layout_type"] != "media_grid" or item["feed_type"] != "media":
                continue
            result.extend([media["media"]
                          for media in item["layout_content"]["medias"]])
        return result


class InstagramAPI():

    # BASE URLS
    URL_BASE = "https://www.instagram.com/"
    URL_LOGIN = "https://www.instagram.com/accounts/login/ajax/"
    URL_LOGOUT = "https://www.instagram.com/accounts/logout/"
    URL_API = "https://www.instagram.com/graphql/query/?query_hash=%s&%s"
    URL_API_v2 = "https://www.instagram.com/graphql/query/?query_id=%s&%s"

    # DATA URLS
    URL_ACTIVITY = "https://www.instagram.com/accounts/activity/?__a=1"
    URL_USER = "https://www.instagram.com/%s/?__a=1"
    URL_MEDIA = "https://www.instagram.com/p/%s/?__a=1"
    URL_TAG = "https://www.instagram.com/explore/tags/%s/?__a=1"
    URL_LOCATION = "https://www.instagram.com/explore/locations/%s/?__a=1"

    # ACTION URLS
    URL_LIKE = "https://www.instagram.com/web/likes/%s/like/"
    URL_UNLIKE = "https://www.instagram.com/web/likes/%s/unlike/"
    URL_COMMENT = "https://www.instagram.com/web/comments/%s/add/"
    URL_UNCOMMENT = "https://www.instagram.com/web/comments/%s/delete/%s/"
    URL_COMMENT_LIKE = "https://www.instagram.com/web/comments/like/%s/"
    URL_COMMENT_UNLIKE = "https://www.instagram.com/web/comments/unlike/%s/"
    URL_FOLLOW = "https://www.instagram.com/web/friendships/%s/follow/"
    URL_UNFOLLOW = "https://www.instagram.com/web/friendships/%s/unfollow/"
    URL_REMOVE_FOLLOWER = "https://www.instagram.com/web/friendships/%s/remove_follower/"
    URL_BLOCK = "https://www.instagram.com/web/friendships/%s/block/"
    URL_UNBLOCK = "https://www.instagram.com/web/friendships/%s/unblock/"
    URL_FOLLOW_TAG = "https://www.instagram.com/web/tags/follow/%s/"
    URL_UNFOLLOW_TAG = "https://www.instagram.com/web/tags/unfollow/%s/"

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
        print("Logout URL_APId")

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
            @return Activity | None
        '''
        response = self._get_response(self.URL_ACTIVITY)
        try:
            response = response['graphql']['user']
            activity = response['activity_feed']['edge_web_activity_feed']["edges"]
            requests = response["edge_follow_requests"]["edges"]
            return {
                'activity_feed': InstagramArray.filter_nodes(activity),
                'follow_requests': InstagramArray.filter_nodes(requests),
            }
        except Exception as e:
            print(get_function_name(), e)
            return None

    def _get_user_followings_by_user_id(self, user_id, end_cursor=""):
        '''
            @param String user_id
            @param String end_cursor
            @return [ User[], String | None ]
        '''
        query_hash = 'd04b0a864b4b54837c0d870b0e77e076'
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
            @param String end_cursor
            @return [ User[], String | None ]
        '''
        query_hash = '17874545323001329'
        query_vars = 'variables={"id":"%s","first":50,"after":"%s"}'
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
            @param String end_cursor
            @return [ User[], String | None ]
        '''
        query_hash = 'c76146de99bb02f6415203be841dd25a'
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
            @param String end_cursor
            @return [ User[], String | None ]
        '''
        query_hash = '17851374694183129'
        query_vars = 'variables={"id":"%s","first":50,"after":"%s"}'
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
            @param String end_cursor
            @return [ User[], String | None ]
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
            @param String end_cursor
            @return [ User[], String | None ]
        '''
        query_hash = '17864450716183058'
        query_vars = 'variables={"shortcode":"%s","first":50,"after":"%s"}'
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
            @param String end_cursor
            @return [ User[], String | None ]
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

    def _get_timeline(self, end_cursor=""):
        '''
            @param String end_cursor
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
            @param String end_cursor
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
            @param String end_cursor
            @return [ Media[], String | None ]
        '''
        query_hash = 'e7e2f4da4b02303f74f0841279e52d76'
        # 003056d32c2554def87228bc3fd9668a
        # e769aa130647d2354c40ea6a439bfc08
        # 8c2a529969ee035a5063f2fc8602a0fd
        # 396983faee97f4b49ccbe105b4daf7a0
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
            @param String end_cursor
            @return [ Media[], String | None ]
        '''
        query_hash = '17880160963012870'
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
            @param String end_cursor
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
        response = self._get_response(self.URL_TAG % tag_name)
        try:
            edges = response["data"]["top"]["sections"]
            return InstagramArray.filter_nodes_v2(edges)
        except Exception as e:
            print(get_function_name(), e)
            return []

    def _get_top_hashtag_feed_by_tag_name_v2(self, tag_name, end_cursor=""):
        '''
            @param String tag_name
            @return Media[]
        '''
        query_hash = 'f92f56d47dc7a55b606908374b43a314'
        query_vars = 'variables={"tag_name":"%s","first":50,"show_ranked":true,"after":"%s"}'
        query_vars = query_vars % (tag_name, end_cursor)
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            response = response["data"]["hashtag"]
            edges = response["edge_hashtag_to_ranked_media"]["edges"]
            return InstagramArray.filter_nodes(edges)
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
        return user_name

    # USER INFO
    def get_user_info(self, user_name):
        '''
            @param String user_name
            @return User | None
        '''
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

        return items[:min(limit, len(items))]

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
