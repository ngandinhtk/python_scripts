import requests
from bs4 import BeautifulSoup

def get_product_details(url):
    """Fetches and scrapes product details from an Amazon URL."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    
    print("Fetching product page...")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: Failed to fetch page. Status code: {response.status_code}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Scrape title
    title_element = soup.select_one('#productTitle')
    title = title_element.get_text(strip=True) if title_element else "Not Found"
    
    # Scrape price
    price_element = soup.select_one('.a-price-whole')
    price_fraction_element = soup.select_one('.a-price-fraction')
    price = "Not Found"
    if price_element and price_fraction_element:
        price = f"{price_element.get_text(strip=True)}{price_fraction_element.get_text(strip=True)}"

    # Scrape description/features
    feature_bullets_element = soup.select_one('#feature-bullets')
    features = []
    if feature_bullets_element:
        features = [li.get_text(strip=True) for li in feature_bullets_element.find_all('li')]
    
    return {
        'title': title,
        'price': price,
        'features': features
    }

def generate_affiliate_link(base_url, affiliate_tag):
    """Appends an affiliate tag to a clean base URL."""
    # Basic URL cleaning
    cleaned_url = base_url.split('?')[0]
    return f"{cleaned_url}?tag={affiliate_tag}"

def main():
    """Main function to run the bot."""
    print("--- TikTok AI Content Bot ---")
    
    # 1. Get user input
    amazon_url = input("Please enter the Amazon product URL: ")
    affiliate_tag = input("Please enter your Amazon affiliate tag (e.g., yourtag-20): ")
    
    # 2. Scrape product data
    product_data = get_product_details(amazon_url)
    
    if not product_data or product_data['title'] == "Not Found":
        print("
Could not retrieve product data. Please check the URL and try again.")
        return

    print("
--- Scraped Product Data ---")
    print(f"Title: {product_data['title']}")
    print(f"Price: ${product_data['price']}")
    print("Features:")
    for feature in product_data['features']:
        print(f"- {feature}")
    print("--------------------------
")
    
    # 3. Generate AI content (This part will be added next)
    print("Generating AI content (script and hashtags)...")
    # Placeholder for AI generation logic
    script = f"Check out this amazing {product_data['title']}! It's perfect for your home. Get it now for just ${product_data['price']}! #AmazonFinds #HomeGadgets"
    
    # 4. Format the affiliate link
    final_link = generate_affiliate_link(amazon_url, affiliate_tag)
    
    # 5. Display the final content package
    print("
--- Your TikTok Content Package ---")
    print("
**Generated Script:**")
    print(script)
    print("
**Affiliate Link:**")
    print(final_link)
    print("
----------------------------------")


if __name__ == "__main__":
    main()
