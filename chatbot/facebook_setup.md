# Facebook Messenger Integration Setup

## 1. Create Facebook App
1. Go to [developers.facebook.com](https://developers.facebook.com).
2. Click **My Apps** → **Create App**.
3. Select **Other** → **Business**.
4. Enter an App Name (e.g., "Chatbot") and create.

## 2. Setup Messenger Product
1. In the App Dashboard, find **Messenger** and click **Set up**.
2. Scroll to **Access Tokens**.
3. Click **Add or Remove Pages** and select the Facebook Page you want to connect.
4. Generate a **Page Access Token** and save it to your `.env` file.

## 3. Configure Environment Variables
Add these to your `.env` file:
```env
FACEBOOK_PAGE_ACCESS_TOKEN=your_page_access_token_here
FACEBOOK_VERIFY_TOKEN=create_a_random_secret_string
```

## 4. Add Webhook Code (FastAPI)
Add a new router or endpoint to your `main.py` or `api/routes.py`.

> **Note**: The endpoint URL must be public (HTTPS).

```python
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse
import os

router = APIRouter()

VERIFY_TOKEN = os.getenv("FACEBOOK_VERIFY_TOKEN")

@router.get("/webhook")
async def verify_webhook(
    mode: str = Query(..., alias="hub.mode"),
    token: str = Query(..., alias="hub.verify_token"),
    challenge: str = Query(..., alias="hub.challenge")
):
    """
    Facebook calls this to verify your server.
    """
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(content=challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/webhook")
async def facebook_webhook(request: Request):
    """
    Facebook sends messages here.
    """
    data = await request.json()
    
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for messaging_event in entry.get("messaging", []):
                if "message" in messaging_event:
                    sender_id = messaging_event["sender"]["id"]
                    message_text = messaging_event["message"].get("text")
                    
                    print(f"Received from {sender_id}: {message_text}")
                    # TODO: Pass this text to your Chatbot/DeepSeek logic
                    # TODO: Send response back to Facebook Graph API
                    
    return {"status": "ok"}
```

## 5. Connect Webhook
1. You need a public HTTPS URL. For local development, use **ngrok**:
1. You need a public HTTPS URL. For local development, use **ngrok**:
1. You need a public HTTPS URL. For local development, use **ngrok**:
   ```bash
   ngrok http 8000
   ```
2. Copy the HTTPS URL (e.g., `https://xyz.ngrok-free.app`).
3. Go back to Facebook Developers → Messenger → **Settings**.
4. Scroll to **Webhooks**.
5. Click **Add Callback URL**.
6. Enter your URL + the route path (e.g., `https://xyz.ngrok-free.app/api/v1/webhook`).
7. Enter the `FACEBOOK_VERIFY_TOKEN` you defined in `.env`.
8. Click **Verify and Save**.

## 6. Subscribe to Page Events
1. Under the **Webhooks** section, click **Add Subscriptions** next to your Page.
2. Select `messages` and `messaging_postbacks`.
3. Click **Save**.dRFzA