import requests
import pickle
import os
import datetime
import re
import random
import time
import json


from utils import (
    dump_json,
    get_project_path,
    get_function_name,
    filter_user_info,
    filter_hashtag_feed,
    filter_hashtag_feed_v2,
    filter_user_feed,
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
            result.extend(item["layout_content"]["medias"])
        return result

    @staticmethod
    def filter_private(items):
        return [
            item for item in items
            if not item["is_private"]
        ]


class InstagramAPI():

    # BASE URLS
    URL_BASE = "https://www.instagram.com/"
    URL_LOGIN = "https://www.instagram.com/accounts/login/ajax/"
    URL_LOGOUT = "https://www.instagram.com/accounts/logout/"
    URL_API = "https://www.instagram.com/graphql/query/?query_hash=%s&variables=%s"
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
    URL_UNCOMMENT = "https://www.instagram.com/web/comments/%s/delete/%s"
    URL_FOLLOW = "https://www.instagram.com/web/friendships/%s/follow/"
    URL_UNFOLLOW = "https://www.instagram.com/web/friendships/%s/unfollow/"
    URL_REMOVE_FOLLOWER = "https://www.instagram.com/web/friendships/%s/remove_follower/"
    URL_BLOCK = "https://www.instagram.com/web/friendships/%s/block/"
    URL_UNBLOCK = "https://www.instagram.com/web/friendships/%s/unblock/"

    # SETTINGS URLS
    URL_EDIT_PROFILE_INFO = "https://www.instagram.com/accounts/edit/"
    URL_EDIT_PROFILE_PIC = "https://www.instagram.com/accounts/web_change_profile_picture/"
    URL_CHANGE_PASSWORD = "https://www.instagram.com/accounts/password/change/"
    URL_SET_PRIVACY = "https://www.instagram.com/accounts/set_private/"
    URL_SET_GENDER = "https://www.instagram.com/accounts/set_gender/"

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
        query_vars = '&variables={"shortcode":"%s","include_reel":true}'
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
        query_vars = '&variables={"user_id":%s,"include_reel":true}'
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
        query_vars = '&variables={"shortcode":"%s","include_reel":true}'
        query_vars = query_vars % short_code
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            user_name = response['data']['shortcode_media']['owner']['reel']['owner']['username']
            return user_name
        except Exception as e:
            print(get_function_name(), e)
            return None

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

    def _get_user_followings_by_user_id(self, user_id, end_cursor=""):
        '''
            @param String user_id
            @param String end_cursor
            @return [ User[], String | None ]
        '''
        query_hash = 'd04b0a864b4b54837c0d870b0e77e076'
        query_vars = '&variables={"id":"%s","first":50,"after":"%s"}'
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
        query_vars = '&variables={"id":"%s","first":50,"after":"%s"}'
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
        query_vars = '&variables={"id":"%s","first":50,"after":"%s"}'
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
        query_vars = '&variables={"id":"%s","first":50,"after":"%s"}'
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
        query_vars = '&variables={"shortcode":"%s","first":50,"after":"%s"}'
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
        query_vars = '&variables={"shortcode":"%s","first":50,"after":"%s"}'
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
        query_vars = '&variables={"shortcode":"%s","first":50,"after":"%s"}'
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

    def _get_timeline_feed(self, end_cursor=""):
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

    def _get_timeline_feed_v2(self, end_cursor=""):
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
        query_vars = '&variables={"id":%s,"first":50,"after":"%s"}'
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
        query_vars = '&variables={"id":"%s","first":50,"after":"%s"}'
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

    def _get_top_hashtag_feed_by_tag_name_v2(self, tag_name):
        '''
            @param String tag_name
            @return Media[]
        '''
        query_hash = 'f92f56d47dc7a55b606908374b43a314'
        query_vars = '&variables={"tag_name":"%s","first":9,"show_ranked":true}'
        query_vars = query_vars % tag_name
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            response = response["data"]["hashtag"]
            edges = response["edge_hashtag_to_ranked_media"]["edges"]
            return InstagramArray.filter(edges)
        except Exception as e:
            print(get_function_name(), e)
            return []

    # USER DATA
    def get_user_id(self, user_name=None, short_code=None):
        if user_name:
            return self._get_user_id_by_user_name(user_name)
        elif short_code:
            return self._get_user_id_by_short_code(short_code)
        return None

    def get_user_name(self, user_id=None, short_code=None):
        user_name = None
        if user_id:
            user_name = self._get_user_name_by_user_id(user_id)
        if not user_name and short_code:
            user_name = self._get_user_name_by_short_code(short_code)
        return user_name

    def get_user_info(self, user_id=None, user_name=None, short_code=None):
        if not user_name:
            user_name = self.get_user_name(user_id, short_code)
        if user_name:
            return self._get_user_info_by_username(user_name)
        return None

    # USER FOLLOWINGS
    def get_user_followings_new(self, user_id, limit=float('inf')):
        [items, end_cursor] = self._get_user_followings_by_user_id(user_id)

        while end_cursor and len(items) < limit:
            time.sleep(random.randint(1, 2))
            [items_new, end_cursor] = self._get_user_followings_by_user_id(
                user_id, end_cursor
            )
            items.extend(items_new)

        return items[:min(limit, len(items))]

    def _get_user_followings(self, user_id=None, user_name=None):
        if not user_id:
            user_id = self._get_user_id_by_user_name(user_name)

        [items, end_cursor] = self._get_user_followings_by_user_id(user_id)
        yield items

        while end_cursor:
            time.sleep(random.randint(1, 2))
            [items, end_cursor] = self._get_user_followings_by_user_id(
                user_id, end_cursor
            )
            yield items

    def get_user_followings(self, user_id=None, user_name=None, filter_private=False, limit=float('inf')):
        result = []
        generator = self._get_user_followings(
            user_id=user_id, user_name=user_name
        )

        for items in generator:
            if filter_private:
                items = InstagramArray.filter_private(items)
            result.extend(items)
            if len(result) >= limit:
                break

        return result[:min(limit, len(result))]

    def get_self_user_followings(self, filter_private=False, limit=float('inf')):
        return self.get_user_followings(
            user_id=self.userid,
            filter_private=filter_private,
            limit=limit
        )

    # USER FOLLOWERS
    def get_user_followers_new(self, user_id, limit=float('inf')):
        [items, end_cursor] = self._get_user_followers_by_user_id(user_id)

        while end_cursor and len(items) < limit:
            time.sleep(random.randint(1, 2))
            [items_new, end_cursor] = self._get_user_followers_by_user_id(
                user_id, end_cursor
            )
            items.extend(items_new)

        return items[:min(limit, len(items))]

    def _get_user_followers(self, user_id=None, user_name=None):
        if not user_id:
            user_id = self._get_user_id_by_user_name(user_name)

        [items, end_cursor] = self._get_user_followers_by_user_id(user_id)
        yield items

        while end_cursor:
            time.sleep(random.randint(1, 2))
            [items, end_cursor] = self._get_user_followers_by_user_id(
                user_id, end_cursor
            )
            yield items

    def get_user_followers(self, user_id=None, user_name=None, filter_private=False, limit=float('inf')):
        result = []
        generator = self._get_user_followers(
            user_id=user_id, user_name=user_name
        )

        for items in generator:
            if filter_private:
                items = InstagramArray.filter_private(items)
            result.extend(items)
            if len(result) >= limit:
                break

        return result[:min(limit, len(result))]

    def get_self_user_followers(self, filter_private=False, limit=float('inf')):
        return self.get_user_followers(
            user_id=self.userid,
            filter_private=filter_private,
            limit=limit
        )

    # USER UNFOLLOWERS
    def get_user_unfollowers(self, user_id=None, user_name=None):
        if not user_id:
            user_id = self._get_user_id_by_user_name(user_name)
        users = self.get_user_followings_all(user_id)
        fans = self.get_user_followers_all(user_id)
        return [[user['username'], user['userid']] for user in users if user not in fans]

    def get_self_user_unfollowers(self):
        return self.get_user_unfollowers(user_id=self.userid)

    # MEDIA LIKERS
    def _get_media_likes(self, short_code):
        [items, end_cursor] = self._get_media_likes_by_short_code(short_code)
        yield items

        while end_cursor:
            time.sleep(random.randint(1, 2))
            [items, end_cursor] = self._get_media_likes_by_short_code(
                short_code, end_cursor
            )
            yield items

    def get_media_likes(self, short_code, filter_private=False, limit=float('inf')):
        result = []
        generator = self._get_media_likes(short_code)

        for items in generator:
            if filter_private:
                items = InstagramArray.filter_private(items)
            result.extend(items)
            if len(result) >= limit:
                break

        return result[:min(limit, len(result))]

    # TIMELINE FEED
    def _get_timeline(self):
        [items, end_cursor] = self._get_timeline_feed()
        yield items

        while end_cursor:
            time.sleep(random.randint(1, 2))
            [items, end_cursor] = self._get_timeline_feed(end_cursor)
            yield items

    def get_timeline(self, limit=float('inf')):
        result = []
        generator = self._get_timeline()

        for items in generator:
            result.extend(items)
            if len(result) >= limit:
                break

        return result[:min(limit, len(result))]

    # USER FEED
    def _get_user_feed(self, user_id=None, user_name=None):
        if not user_id:
            user_id = self._get_user_id_by_user_name(user_name)

        [items, end_cursor] = self._get_user_feed_by_user_id(user_id)
        yield items

        while end_cursor:
            time.sleep(random.randint(1, 2))
            [items, end_cursor] = self._get_user_feed_by_user_id(
                user_id, end_cursor
            )
            yield items

    def get_user_feed(self, user_id=None, user_name=None, limit=float('inf')):
        result = []
        generator = self._get_user_feed(
            user_id=user_id, user_name=user_name
        )

        for items in generator:
            result.extend(items)
            if len(result) >= limit:
                break

        if not result:
            # if not user_name:
            #     user_name = self.get_user_name(user_id=user_id)
            result = self._get_user_feed_by_user_name(user_name)

        return result[:min(limit, len(result))]

    def get_self_user_feed(self, limit=float('inf')):
        return self.get_user_feed(
            user_id=self.userid,
            user_name=self.username,
            limit=limit
        )

    # TAGGED FEED
    def get_user_tagged_feed(self, user_id=None, user_name=None):
        if not user_id:
            user_id = self._get_user_id_by_user_name(user_name)
        [medias, _] = self._get_user_tagged_feed_by_user_id(user_id)
        return medias

    def get_self_user_tagged_feed(self):
        return self.get_user_tagged_feed(user_id=self.userid)

    def get_user_tagged_feed_all(self, user_id=None, user_name=None):
        if not user_id:
            user_id = self._get_user_id_by_user_name(user_name)
        [medias, end_cursor] = self._get_user_tagged_feed_by_user_id(user_id)
        while end_cursor:
            time.sleep(random.randint(1, 2))
            [medias_new, end_cursor] = self._get_user_tagged_feed_by_user_id(
                user_id, end_cursor
            )
            medias.extend(medias_new)
        return medias

    def get_self_user_tagged_feed_all(self):
        return self.get_user_tagged_feed_all(user_id=self.userid)

    # HASHTAG FEED
    def get_top_hashtag_feed(self, tag_name):
        result = self._get_top_hashtag_feed_by_tag_name(tag_name)
        if len(result):
            return result
        return self._get_top_hashtag_feed_by_tag_name_v2(tag_name)

    # TAKE ACTIONS
    def like_media(self, media_id=None, short_code=None):
        if not media_id:
            media_id = self._get_media_id_by_short_code(short_code)
        res = self.s.post(self.URL_LIKE % media_id)
        return res.status_code == 200

    def unlike_media(self, media_id=None, short_code=None):
        if not media_id:
            media_id = self._get_media_id_by_short_code(short_code)
        res = self.s.post(self.URL_UNLIKE % media_id)
        return res.status_code == 200

    def comment_media(self, text, media_id=None, short_code=None, replied_to_comment_id=None):
        if not media_id:
            media_id = self._get_media_id_by_short_code(short_code)
        data = {
            'comment_text': text,
            'replied_to_comment_id': replied_to_comment_id,
        }
        res = self.s.post(self.URL_COMMENT % media_id, data=data)
        return res.status_code == 200

    def uncomment_media(self, comment_id, media_id=None, short_code=None):
        if not media_id:
            media_id = self._get_media_id_by_short_code(short_code)
        res = self.s.post(self.URL_UNCOMMENT % (media_id, comment_id))
        return res.status_code == 200

    def follow_user(self, user_id=None, user_name=None, short_code=None):
        if not user_id:
            user_id = self.get_user_id(user_name, short_code)
        res = self.s.post(self.URL_FOLLOW % user_id)
        return res.status_code == 200

    def unfollow_user(self, user_id=None, user_name=None, short_code=None):
        if not user_id:
            user_id = self.get_user_id(user_name, short_code)
        res = self.s.post(self.URL_UNFOLLOW % user_id)
        return res.status_code == 200

    def remove_follower(self, user_id=None, user_name=None, short_code=None):
        if not user_id:
            user_id = self.get_user_id(user_name, short_code)
        res = self.s.post(self.URL_REMOVE_FOLLOWER % user_id)
        return res.status_code == 200

    def block_user(self, user_id=None, user_name=None, short_code=None):
        if not user_id:
            user_id = self.get_user_id(user_name, short_code)
        res = self.s.post(self.URL_BLOCK % user_id)
        return res.status_code == 200

    def unblock_user(self, user_id=None, user_name=None, short_code=None):
        if not user_id:
            user_id = self.get_user_id(user_name, short_code)
        res = self.s.post(self.URL_UNBLOCK % user_id)
        return res.status_code == 200

    # ACCOUNT SETTINGS
    def change_password(self, password):
        time = int(datetime.datetime.now().timestamp())
        data = {
            "enc_old_password": f"#PWD_INSTAGRAM_BROWSER:0:{time}:{self.password}",
            "enc_new_password1": f"#PWD_INSTAGRAM_BROWSER:0:{time}:{password}",
            "enc_new_password2": f"#PWD_INSTAGRAM_BROWSER:0:{time}:{password}",
        }
        res = self.s.post(self.URL_CHANGE_PASSWORD, data=data)
        return res.status_code == 200

    def set_privacy(self, private):
        data = {"is_private": private}
        res = self.s.post(self.URL_SET_PRIVACY, data=data)
        return res.status_code == 200
