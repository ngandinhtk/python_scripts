# Google Sheets Configuration Issue

## Current Problem
The `GOOGLE_SHEETS_URL` environment variable points to a personal development Google Sheet that contains **personal coaching scenarios, NOT rental listing data**.

### Current Sheet Structure
- **URL**: https://docs.google.com/spreadsheets/d/1DfG2-OpEBhgMHMz7UU_BA3AtWY_v1ANzOY3O8klrsOs/
- **Columns**: 
  1. Kịch bản lặp lại (Repeating scenarios)
  2. Kịch bản sửa đổi (Modified scenarios)
  3. Kịch bản ngẫu hứng (Improvisation scenarios)
  4. Affirmation / Hành động cụ thể (Affirmations/Actions)
  5. Column 5
  6. Column 6

- **Content**: Vietnamese life coaching and personal development scenarios

## What's Needed
To post rental listings to Facebook Marketplace, you need a Google Sheet with these columns:

### Required Columns:
- **Title** - Listing title (e.g., "2 Bed, 1 Bath Apartment in Downtown")
- **Price per month** - Monthly rent price (numeric)
- **Location** - Property location/address
- **Rental description** - Full description of the property

### Optional Columns:
- **Number of bedrooms** - Number of bedrooms
- **Number of bathrooms** - Number of bathrooms  
- **Rental type** - Type of rental (Apartment, House, Room, etc.)
- **Date available** - When the rental is available
- **ImagePath** - URL to an image of the property
- **Pet Friendly** - Yes/No
- **Laundry Type** - In-unit/Shared/No
- **Parking Type** - Off-street/On-street/Garage/No
- **AC Type** - Central/Window/No
- **Heating Type** - Central/Individual/No

### Example Google Sheet Structure:
```
Title | Price per month | Location | Rental description | Number of bedrooms | Number of bathrooms | ImagePath | Status
2 Bed Downtown | 1500 | 123 Main St | Spacious 2 bed apartment... | 2 | 1 | https://... | in progress
Studio Midtown | 1200 | 456 Oak Ave | Cozy studio apartment... | 0 | 1 | https://... | in progress
```

## Solution Steps:
1. **Create a new Google Sheet** with rental listing data using the columns above
2. **Update .env file** with the new Google Sheets URL:
   ```
   GOOGLE_SHEETS_URL=https://docs.google.com/spreadsheets/d/YOUR_NEW_SHEET_ID/edit
   ```
3. **Run bot.py again** with the correct data

## How to Create a New Sheet:
1. Go to https://docs.google.com/spreadsheets
2. Click "New" → "Blank spreadsheet"
3. Add column headers matching the structure above
4. Add your rental listings as rows
5. Share the sheet with your service account email (from credentials.json)
6. Copy the Sheet URL and update the .env file

## Current Status:
- ✓ Bot code is working correctly
- ✓ Google Sheets API connection works
- ✗ Google Sheet contains wrong data type
- ✗ Column names don't match expected rental listing format
