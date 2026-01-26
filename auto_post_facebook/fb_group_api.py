import os
import requests

def post_text_to_group(group_id: str, message: str, access_token: str) -> dict:
    """Post a text message to a Facebook group using Graph API.

    Requires `publish_to_groups` permission on the access token and that the
    token is from a user who is member/admin of the group (or the app is added
    to the group).
    """
    url = f"https://graph.facebook.com/v16.0/{group_id}/feed"
    payload = {
        "message": message,
        "access_token": access_token,
    }

    resp = requests.post(url, data=payload, timeout=30)
    return resp.json()


def post_photo_to_group(group_id: str, caption: str, image_path_or_url: str, access_token: str) -> dict:
    """Post a photo to a Facebook group.

    If `image_path_or_url` starts with http(s) it will be sent as `url`, otherwise
    the function will try to open the local file and upload it.
    """
    url = f"https://graph.facebook.com/v16.0/{group_id}/photos"

    if image_path_or_url.startswith("http://") or image_path_or_url.startswith("https://"):
        payload = {
            "caption": caption,
            "url": image_path_or_url,
            "access_token": access_token,
        }
        resp = requests.post(url, data=payload, timeout=30)
        return resp.json()
    else:
        if not os.path.exists(image_path_or_url):
            return {"error": {"message": f"File not found: {image_path_or_url}"}}

        with open(image_path_or_url, "rb") as f:
            files = {"source": f}
            payload = {
                "caption": caption,
                "access_token": access_token,
            }
            resp = requests.post(url, data=payload, files=files, timeout=60)
            return resp.json()


if __name__ == "__main__":
    # Quick local test example (won't run correctly without valid token/group)
    import os
    group = os.getenv("FB_GROUP_ID")
    token = os.getenv("FB_GROUP_TOKEN")
    msg = "Test post from script"
    if group and token:
        print(post_text_to_group(group, msg, token))
    else:
        print("Set FB_GROUP_ID and FB_GROUP_TOKEN in environment to test")
