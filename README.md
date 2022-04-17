# Instagram API

### Install

Download repo to your project directory.

### Initialization

This is the way to initialize the InstagramAPI.

```python
from api import InstagramAPI

api = InstagramAPI(config, force_login=False)
```

The parameter `config` is required and has the following shape.

The `userid` can initially be an empty string and filled in afterwards.
It is used in some functions to retrieve data about the logged in account.
There is a function to get the `userid` called `get_user_id`.

```json
{
  "userid": "ig_userid",
  "username": "ig_username",
  "password": "ig_password"
}
```

The parameter `force_login` is optional and can be used to relogin if there are cookies from a previous login because the cookies are automatically cached per account:

`~/Documents/instagram-scripts/accounts/{ig_username}/web.cookies`

### User Data

It is possible to retrieve the userid of an account either by the username or by the shortcode of an post from the account.

```python
userid = api.get_user_id(user_name="world_record_egg")
# or
userid = api.get_user_id(short_code="BsOGulcndj-")
```

It is possible to retrieve the username of an account by either the userid or the shortcode of an post from the account.

```python
username = api.get_user_name(user_id="10013772027")
# or
username = api.get_user_name(short_code="BsOGulcndj-")
```

### User Info

It is possible to retrieve some basic account information by the username.

```python
info = api.get_user_info(user_name="world_record_egg")
# or
info = api.get_self_user_info()
```

This function returns basic account information as follows

```json
{
  "userid": "10013772027",
  "username": "world_record_egg",
  "private": false,
  "following": 1,
  "followers": 4784873,
  "posts": 1
}
```

### General Information

The package provides a function called `manipulate` which can be used to reduce every item regarding its keys. This is possible up to one level of nesting.

The function `manipulate` takes 2 parameters, namely `keys` and `predicate`.
The `keys` can be passed as either a list or preferably a dict which allows the mentioned nesting as well as renaming the keys.
The `predicate` can be passed optionally and allows filtering the items.

```python
from api import manipulate

def is_not_private(item):
    return 'is_private' not in item or item['is_private'] == False

def is_not_liked(item):
    return 'viewer_has_liked' not in item or item['viewer_has_liked'] == False

# keys as list
manipulate_keys = manipulate([ 'key_1', 'key_2', ... ])

# keys as dict
manipulate_dict = manipulate({ 'new_key': 'old_key', ... })

# keys as dict & predicate
manipulate_user = manipulate({
    'userid': 'id',
    'username': 'username',
    'private': 'is_private',
}, is_not_private)
```

### User Data, Media Data, etc.

The parameters `limit` and `manipulate` are **optional**. The value of `limit` decides the maximum number of items to retrieve. If there are less items than the `limit`, all items get returned. The function `manipulate` can be used to extract only the wanted information from the resulting items.

#### user followings

- get_user_followings
- get_self_user_followings
- get_user_followings_v2
- get_self_user_followings_v2

#### user followers

- get_user_followers
- get_self_user_followers
- get_user_followers_v2
- get_self_user_followers_v2

#### media likes

- get_media_likes
- get_media_likes_v2

#### media comments

- get_media_comments

#### timeline

- get_timeline
- get_timeline_v2

#### user feed

- get_user_feed
- get_self_user_feed
- get_user_feed_v2
- get_self_user_feed_v2
- get_user_feed_v3
- get_self_user_feed_v3

#### user tagged feed

- get_user_tagged_feed
- get_self_user_tagged_feed

### Take Actions

These functions can be used to take actions with the logged in account.

- like_media
- unlike_media
- comment_media
- uncomment_media
- follow_user
- unfollow_user
- remove_follower
- block_user
- unblock_user
- follow_tag
- unfollow_tag
