import requests
import pickle
import os
import datetime
import re
import random
import time


from utils import (
    dump_json,
    get_project_path,
    get_function_name,
    filter_user_info,
    filter_hashtag_feed,
    filter_hashtag_feed_v2,
    filter_user_feed,
)


class InstagramAPI():

    # BASE URLS
    URL_BASE = "https://www.instagram.com/"
    URL_LOGIN = "https://www.instagram.com/accounts/login/ajax/"
    URL_LOGOUT = "https://www.instagram.com/accounts/logout/"
    URL_API = "https://www.instagram.com/graphql/query/?query_hash=%s&variables=%s"

    # DATA URLS
    URL_USER = "https://www.instagram.com/%s/?__a=1"
    URL_MEDIA = "https://www.instagram.com/p/%s/?__a=1"
    URL_TAG = "https://www.instagram.com/explore/tags/%s/?__a=1"
    URL_LOCATION = "https://www.instagram.com/explore/locations/%s/?__a=1"

    # ACTION URLS
    URL_LIKE = "https://www.instagram.com/web/likes/%s/like/"
    URL_UNLIKE = "https://www.instagram.com/web/likes/%s/unlike/"
    URL_FOLLOW = "https://www.instagram.com/web/friendships/%s/follow/"
    URL_UNFOLLOW = "https://www.instagram.com/web/friendships/%s/unfollow/"

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
        response = self._get_response(self.URL_USER % user_name)
        try:
            pk = response['graphql']['user']['id']
            return pk
        except Exception as e:
            print(get_function_name(), e)
            return None

    def _get_user_id_by_short_code(self, short_code):
        query_hash = '6ff3f5c474a240353993056428fb851e'
        query_vars = '&variables={"shortcode":"%s","include_reel":true}'
        query_vars = query_vars % short_code
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            pk = response['data']['shortcode_media']['owner']['reel']['owner']['id']
            return pk
        except Exception as e:
            print(get_function_name(), e)
            return None

    def _get_user_name_by_user_id(self, user_id):
        query_hash = 'd4d88dc1500312af6f937f7b804c68c3'
        # c9100bf9110dd6361671f113dd02e7d6
        query_vars = '&variables={"user_id":%s,"include_chaining":false,"include_reel":true}'
        query_vars = query_vars % user_id
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            username = response['data']['user']['reel']['owner']['username']
            return username
        except Exception as e:
            print(get_function_name(), e)
            return None

    def _get_user_name_by_short_code(self, short_code):
        query_hash = '6ff3f5c474a240353993056428fb851e'
        query_vars = '&variables={"shortcode":"%s","include_reel":true}'
        query_vars = query_vars % short_code
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            username = response['data']['shortcode_media']['owner']['reel']['owner']['username']
            return username
        except Exception as e:
            print(get_function_name(), e)
            return None

    def _get_user_info_by_username(self, user_name):
        response = self._get_response(self.URL_USER % user_name)
        try:
            user = response['graphql']['user']
            return {
                "id": user['id'],
                "username": user['username'],
                "following": user['edge_follow']['count'],
                "followers": user['edge_followed_by']['count'],
                "posts": user['edge_owner_to_timeline_media']['count']
            }
        except Exception as e:
            print(get_function_name(), e)
            return None

    def _get_media_id_by_short_code(self, short_code):
        response = self._get_response(self.URL_MEDIA % short_code)
        try:
            media_id = response['items'][0]['id']
            media_id = media_id.split("_")[0]
            return media_id
        except Exception as e:
            print(get_function_name(), e)
            return None

    def _get_user_followings(self, user_id, check_private, end_cursor=""):
        query_hash = 'd04b0a864b4b54837c0d870b0e77e076'
        query_vars = '&variables={"id":"%s","include_reel":false,"fetch_mutual":false,"first":50,"after":"%s"}'
        query_vars = query_vars % (user_id, end_cursor)
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            response = response['data']['user']['edge_follow']
            edges = response["edges"]
            cursor = response["page_info"]

            users = filter_user_info(edges, check_private)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [users, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_user_followers(self, user_id, check_private, end_cursor=""):
        query_hash = 'c76146de99bb02f6415203be841dd25a'
        query_vars = '&variables={"id":"%s","include_reel":false,"fetch_mutual":false,"first":50,"after":"%s"}'
        query_vars = query_vars % (user_id, end_cursor)
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            response = response['data']['user']['edge_followed_by']
            edges = response["edges"]
            cursor = response["page_info"]

            users = filter_user_info(edges, check_private)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [users, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_media_likers(self, short_code, check_private, end_cursor=""):
        query_hash = 'd5d763b1e2acf209d62d22d184488e57'
        # d5d763b1e2acf209d62d22d184488e57
        query_vars = '&variables={"shortcode":"%s","include_reel":false,"first":50,"after":"%s"}'
        query_vars = query_vars % (short_code, end_cursor)
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            response = response['data']['shortcode_media']['edge_liked_by']
            edges = response["edges"]
            cursor = response["page_info"]

            users = filter_user_info(edges, check_private)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [users, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_user_feed_by_user_name(self, user_name):
        response = self._get_response(self.URL_USER % user_name)
        try:
            response = response['graphql']['user']
            edges = response['edge_owner_to_timeline_media']['edges']
            medias = filter_user_feed(edges)
            return medias
        except Exception as e:
            print(get_function_name(), e)
            return []

    def _get_user_feed_by_user_id(self, user_id, end_cursor=""):
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

            medias = filter_user_feed(edges)
            end_cursor = cursor["end_cursor"] if cursor["has_next_page"] else None
            return [medias, end_cursor]
        except Exception as e:
            print(get_function_name(), e)
            return [[], None]

    def _get_top_hashtag_feed(self, tag_name):
        response = self._get_response(self.URL_TAG % tag_name)
        try:
            sections = response["data"]["top"]["sections"]
            medias = filter_hashtag_feed(sections)
            return medias
        except Exception as e:
            print(get_function_name(), e)
            return []

    def _get_top_hashtag_feed_v2(self, tag_name):
        query_hash = 'f92f56d47dc7a55b606908374b43a314'
        query_vars = '&variables={"tag_name":"%s","first":9,"show_ranked":true}'
        query_vars = query_vars % tag_name
        response = self._get_response(self.URL_API % (query_hash, query_vars))
        try:
            response = response["data"]["hashtag"]
            edges = response["edge_hashtag_to_ranked_media"]["edges"]
            medias = filter_hashtag_feed_v2(edges)
            return medias
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
        if user_id:
            return self._get_user_name_by_user_id(user_id)
        elif short_code:
            return self._get_user_name_by_short_code(short_code)
        return None

    def get_user_info(self, user_id=None, user_name=None, short_code=None):
        if user_id and not user_name:
            user_name = self.get_username(user_id, short_code)
        if user_name:
            return self._get_user_info_by_username(user_name)
        return None

    # FOLLOW DATA
    def get_user_followings(self, user_id=None, user_name=None, check_private=False):
        if not user_id:
            user_id = self._get_user_id_by_user_name(user_name)
        [users, _] = self._get_user_followings(user_id, check_private)
        return users

    def get_user_followings_all(self, user_id=None, user_name=None, check_private=False):
        if not user_id:
            user_id = self._get_user_id_by_user_name(user_name)
        [users, end_cursor] = self._get_user_followings(user_id, check_private)
        while end_cursor:
            time.sleep(random.randint(1, 2))
            [users_new, end_cursor] = self._get_user_followings(
                user_id, check_private, end_cursor
            )
            users.extend(users_new)
        return users

    def get_user_followers(self, user_id=None, user_name=None, check_private=False):
        if not user_id:
            user_id = self._get_user_id_by_user_name(user_name)
        [users, _] = self._get_user_followers(user_id, check_private)
        return users

    def get_user_followers_all(self, user_id=None, user_name=None, check_private=False):
        if not user_id:
            user_id = self._get_user_id_by_user_name(user_name)
        [users, end_cursor] = self._get_user_followers(user_id, check_private)
        while end_cursor:
            time.sleep(random.randint(1, 2))
            [users_new, end_cursor] = self._get_user_followers(
                user_id, check_private, end_cursor
            )
            users.extend(users_new)
        return users

    def get_user_unfollowers(self, user_id=None, user_name=None):
        if not user_id:
            user_id = self._get_user_id_by_user_name(user_name)
        users = self.get_user_followings_all(user_id)
        fans = self.get_user_followers_all(user_id)
        return [user['username'] for user in users if user not in fans]

    # LIKER DATA
    def get_media_likers(self, short_code, check_private=False):
        [users, _] = self._get_media_likers(short_code, check_private)
        return users

    def get_media_likers_all(self, short_code, check_private=False):
        [users, end_cursor] = self._get_media_likers(short_code, check_private)
        while end_cursor:
            time.sleep(random.randint(1, 2))
            [users_new, end_cursor] = self._get_media_likers(
                short_code, check_private, end_cursor
            )
            users.extend(users_new)
        return users

    # FEED DATA
    def get_user_feed(self, user_id=None, user_name=None):
        if not user_id:
            user_id = self._get_user_id_by_user_name(user_name)
        [medias, _] = self._get_user_feed_by_user_id(user_id)
        if len(medias):
            return medias
        return self._get_user_feed_by_user_name(user_name)

    def get_user_feed_all(self, user_id=None, user_name=None):
        if not user_id:
            user_id = self._get_user_id_by_user_name(user_name)
        [medias, end_cursor] = self._get_user_feed_by_user_id(user_id)
        while end_cursor:
            time.sleep(random.randint(1, 2))
            [medias_new, end_cursor] = self._get_user_feed_by_user_id(user_id)
            medias.extend(medias_new)
        if len(medias):
            return medias
        return self._get_user_feed_by_user_name(user_name)

    def get_top_hashtag_feed(self, tag_name):
        result = self._get_top_hashtag_feed(tag_name)
        if len(result):
            return result
        return self._get_top_hashtag_feed_v2(tag_name)

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
