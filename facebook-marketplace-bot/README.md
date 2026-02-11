# Facebook Marketplace Rental Bot

This bot automates posting rental listings to Facebook Marketplace using data from a Google Sheet.

- **Status Filtering:** Only posts listings marked "in progress" in your Google Sheet.

## Setup

### 1. Install Dependencies

Make sure you have Python installed. Then, install the required packages:

```bash
pip install -r requirements.txt
```

### 2. Set up your `.env` file

Create a `.env` file in the same directory as `bot.py` with the following content:

```env
FACEBOOK_EMAIL=your_facebook_email@example.com
FACEBOOK_PASSWORD=your_facebook_password
GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/your_sheet_id/edit
GOOGLE_CREDS_FILE=credentials.json
```

- `FACEBOOK_EMAIL` and `FACEBOOK_PASSWORD`: Your Facebook login credentials.
- `GOOGLE_SHEETS_URL`: The URL of your Google Sheet containing the rental listings.
- `GOOGLE_CREDS_FILE`: The name of the JSON file with your Google service account credentials (default is `credentials.json`).

### 3. Set up your Google Sheet

1.  Follow the instructions in `GOOGLE_SHEETS_SETUP.md` to create a service account and get your `credentials.json` file.
2.  Create a Google Sheet with the following headers in the first row. Please refer to `GOOGLE_SHEETS_SETUP.md` for full details on the required columns including the new `Status` column:
    - `Rental type`: The type of rental (e.g., "Apartment/condo", "House").
    - `Date available`: The date the rental is available.
    - `Number of bedrooms`: The number of bedrooms.
    - `Number of bathrooms`: The number of bathrooms.
    - `Price per month`: The monthly rent.
    - `Location`: The location of the rental.
    - `Rental description`: The description of the rental.
    - `ImagePath`: The URL of the image for the listing.
    - `status`: (Required for filtering) Set to "in progress" for listings you want to post.

### 4. Run the Bot

To start the bot, run the following command in your terminal:

```bash
python bot.py
```

The bot will then:
1.  Log in to Facebook.
2.  Fetch the rental listings from your Google Sheet.
3.  Post each listing to Facebook Marketplace.

## How it Works

The bot uses Selenium to automate a Chrome browser. It navigates to the Facebook Marketplace rental creation page, fills in the form with the data from your Google Sheet, uploads the image, and submits the listing.

## Disclaimer

This bot is for educational purposes only. Use it responsibly and at your own risk. Automating social media interactions may be against the terms of service of the platform. The developers of this bot are not responsible for any consequences of its use.
