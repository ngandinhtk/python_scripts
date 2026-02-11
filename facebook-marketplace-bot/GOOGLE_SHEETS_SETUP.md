# Google Sheets Integration Setup Guide

This bot now pulls product data from a Google Sheet and automatically posts multiple items to Facebook Marketplace.

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (click "Select a project" > "New Project")
3. Name it something like "FB Marketplace Bot"

## Step 2: Enable Google Sheets API

1. In the Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for "Google Sheets API"
3. Click on it and press **Enable**

## Step 3: Create a Service Account

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **Service Account**
3. Fill in the service account name (e.g., "fb-marketplace-bot")
4. Click **Create and Continue**
5. Grant the service account **Editor** role (not required, but simplest)
6. Click **Continue** and then **Done**

## Step 4: Create and Download JSON Key

1. On the Credentials page, find your service account and click on it
2. Go to the **Keys** tab
3. Click **Add Key** > **Create new key**
4. Choose **JSON** and click **Create**
5. A JSON file will download automatically
6. **Save this file as `credentials.json` in your bot directory** (same folder as `bot.py`)

⚠️ **Important:** Keep this file private! It contains your Google Cloud credentials.

## Step 5: Create Your Google Sheet

1. Go to [Google Sheets](https://sheets.google.com/)
2. Create a new spreadsheet
3. Set up your first row with headers:
   ```
   Rental type | Date available | Number of bedrooms | Number of bathrooms | Price per month | Location | Rental description | ImagePath | status
   ```

4. Add your products in subsequent rows. Example:

   | Rental type | Date available | Number of bedrooms | Number of bathrooms | Price per month | Location | Rental description | ImagePath | status |
   |---|---|---|---|---|---|---|---|---|
   | Apartment/condo | 2024-10-01 | 2 | 1 | 1500 | New York, NY | Bright and spacious 2-bedroom apartment. | ./images/apartment.jpg | in progress |
   | House | 2024-11-15 | 4 | 3 | 3000 | San Francisco, CA | Large house with a backyard. | ./images/house.jpg | completed |
   | Townhouse | 2024-12-01 | 3 | 2.5 | 2200 | Chicago, IL | Modern townhouse with great amenities. | ./images/townhouse.jpg | in progress |

### Status Column

The bot now filters listings based on a "Status" column in your Google Sheet. Only listings with the status "in progress" (case-insensitive) will be posted to Facebook Marketplace. If a "Status" column is not found in your sheet, all listings will be processed.

5. Share the sheet with your service account:
   - Click **Share** (top right)
   - Copy your service account email from the `credentials.json` file (it looks like `service-account@project-id.iam.gserviceaccount.com`)
   - Paste it in the Share box and give it **Editor** access
   - Click **Share**

## Step 6: Update Your .env File

Add these variables to your `.env` file:

```env
FACEBOOK_EMAIL=your_facebook_email@gmail.com
FACEBOOK_PASSWORD=your_facebook_password
GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
GOOGLE_CREDS_FILE=credentials.json
```

**To find your sheet ID:**
- Open your Google Sheet
- Copy the URL
- The sheet ID is the long alphanumeric string between `/d/` and `/edit`
- Example: `https://docs.google.com/spreadsheets/d/1A2B3C4D5E6F7G8H/edit`
- Your ID is: `1A2B3C4D5E6F7G8H`

## Step 7: Prepare Product Images

- Upload images to your bot folder (e.g., in an `images/` subfolder)
- Reference them in the Google Sheet with relative paths like `./images/lamp.jpg` or `./placeholder.png`
- Make sure the image files actually exist

## Step 8: Run the Bot

```bash
python bot.py
```

The bot will:
1. ✓ Connect to your Google Sheet
2. ✓ Fetch all products
3. ✓ Log in to Facebook
4. ✓ Post each product to Marketplace with auto-retry on 2FA
5. ✓ Display progress and save screenshots on errors

## Troubleshooting

### "Error: Google credentials file 'credentials.json' not found"
- Download the JSON key from Google Cloud Console (see Step 4)
- Place it in the same folder as `bot.py`

### "Buid credentials file denied"
- The service account email wasn't added to the spreadsheet's share list
- Re-do Step 5 (Share section)

### "Could not find title input"
- Facebook may have changed the form structure
- The bot will save a screenshot (`error_product_*.png`) showing what it sees
- You may need to update the XPath selectors in the code

### "Two-factor authentication detected"
- The bot will pause and wait up to 60 seconds for you to complete 2FA in the browser
- Complete the authentication in the browser window that opens

## Example Google Sheet Structure

```
A              | B     | C              | D                                    | E
Title          | Price | Category       | Description                          | ImagePath
Wooden Chair   | 45    | Furniture      | Classic wooden chair, very sturdy   | ./images/chair.jpg
Desk Lamp      | 20    | Furniture      | Modern LED desk lamp                 | ./images/lamp.jpg
Used Textbook  | 30    | Books          | Economics 101 textbook, 3rd edition | ./images/book.jpg
```

## Notes

- **Batch posting:** The bot posts one product at a time with 5-second delays between posts
- **Error handling:** If one product fails, the bot continues with the next one
- **Screenshots:** Error screenshots are saved as `error_product_X.png` for debugging
- **Rate limits:** Facebook may rate-limit or require additional verification if posting too many items quickly

---

Good luck! 🚀
