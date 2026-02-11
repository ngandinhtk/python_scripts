import json

def load_cookies(driver, path="cookies.json"):
    with open(path, "r") as f:
        cookies = json.load(f)
    for cookie in cookies:
        # The 'sameSite' attribute from browser cookie exports can be 'no_restriction' or 'unspecified'
        # which are not valid for Selenium's add_cookie method. It needs to be 'Strict', 'Lax', or 'None'.
        if 'sameSite' in cookie and cookie['sameSite'] not in ['Strict', 'Lax', 'None']:
            if cookie['sameSite'].lower() == 'no_restriction':
                cookie['sameSite'] = 'None'
            else: # For 'unspecified' and other potential invalid values
                cookie['sameSite'] = 'Lax'

        # Selenium expects an integer for expiry, but it can be a float in the JSON.
        if 'expirationDate' in cookie:
            cookie['expirationDate'] = int(cookie['expirationDate'])

        try:
            driver.add_cookie(cookie)
        except Exception as e:
            print(f"Warning: Could not add cookie '{cookie.get('name')}'. Error: {e}")
