# DeepSeek API Integration Setup

## 1. Get DeepSeek API Key

1. Visit [https://platform.deepseek.com](https://platform.deepseek.com)
2. Sign up or log in to your account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the API key (keep it SECRET - never commit to git)

## 2. Configure Environment Variables

Create a `.env` file in the chatbot root directory:

```bash
cp .env.example .env
```

Edit `.env` and add your DeepSeek API key:

```
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TEMPERATURE=0.7
DEEPSEEK_MAX_TOKENS=1000
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Run the Chatbot

```bash
python main.py
```

The API will be available at `http://localhost:8000`

## 5. API Endpoints

### Chat Endpoint
**POST** `/api/v1/chat`

Request:
```json
{
  "content": "Your message here",
  "session_id": "optional-session-id"
}
```

Response:
```json
{
  "session_id": "session-id",
  "role": "assistant",
  "content": "DeepSeek response here"
}
```

### Get Chat History
**GET** `/api/v1/history/{session_id}`

Response:
```json
{
  "session_id": "session-id",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

### Health Check
**GET** `/health`

Response:
```json
{"status": "ok"}
```

## 6. Configuration Options

In `.env`, you can customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | - | Your DeepSeek API key (required) |
| `DEEPSEEK_MODEL` | deepseek-chat | Model to use for chat |
| `DEEPSEEK_TEMPERATURE` | 0.7 | Response creativity (0-2) |
| `DEEPSEEK_MAX_TOKENS` | 1000 | Max response length |
| `SHEETS_SYNC_INTERVAL` | 300 | Google Sheets sync interval (seconds) |

## 7. Troubleshooting

### "DEEPSEEK_API_KEY is not set" error
- Make sure `.env` file exists in the root directory
- Check that `DEEPSEEK_API_KEY` is set with your actual API key
- Restart the application after changing `.env`

### Connection errors
- Verify DeepSeek API is accessible: `https://api.deepseek.com/v1`
- Check firewall/proxy settings
- Verify API key is valid on DeepSeek platform

### Rate limiting
- DeepSeek may have rate limits on free tier
- Check your account limits at https://platform.deepseek.com
