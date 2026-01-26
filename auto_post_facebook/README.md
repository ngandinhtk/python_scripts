# auto_post_facebook — Group posting helper

This repository contains scripts to help automate posting to Facebook (pages/groups) and marketplace.

Important: Automating actions on Facebook requires correct permissions and compliance with Facebook Platform Policies. Use tokens only for accounts you control.

## Quick guide — obtain token & set up

1. Create a Facebook App at https://developers.facebook.com/apps
2. Add the `groups_access_member_info` and `publish_to_groups` permissions in App Review if you need production access.
3. For testing, you can use the Graph API Explorer to generate a user access token with `publish_to_groups` (your user must be member/admin of the target group). For production, implement OAuth flow to obtain a long-lived user token.
4. If you want to post photos to a group, either:
   - Use the user token (the user must have rights in the group), or
   - Add the App to the group (Group admins can add apps) so the app can post.
5. Get the group ID by opening the group and looking up the ID in the URL or using the Graph API.

## Usage examples

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Set environment variables (or create a `.env` from `.env.example`):

```
FB_GROUP_ID=your_group_id
FB_GROUP_TOKEN=your_user_access_token
```

Python example (text post):

```python
from fb_group_api import post_text_to_group
import os

group = os.getenv('FB_GROUP_ID')
token = os.getenv('FB_GROUP_TOKEN')
print(post_text_to_group(group, 'Hello group from script', token))
```

Python example (photo post):

```python
from fb_group_api import post_photo_to_group
import os

group = os.getenv('FB_GROUP_ID')
token = os.getenv('FB_GROUP_TOKEN')
print(post_photo_to_group(group, 'Caption here', 'https://example.com/image.jpg', token))
```

## Notes & Troubleshooting

- If you receive permission errors, check that the token includes `publish_to_groups` and that the user is allowed to post to the group.
- Long-lived tokens: exchange short-lived user tokens for long-lived tokens via the OAuth endpoints; cycles and refresh rules apply.
- Respect Facebook policy: do not spam and obtain user consent where necessary.
