import requests
import json
import urllib.parse
from bs4 import BeautifulSoup

url = "https://www.1024tera.com/sharing/link?surl=uOH1rigHDKBaNt01_NEQPg"
encoded_url = urllib.parse.quote_plus(url)
print(f"Requesting teradownloader for: {encoded_url}")

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

try:
    # Let's see if there is an API endpoint or we scrape the HTML
    # A common pattern for these sites is a POST to /api or /get-link
    # But let's just fetch the page first
    res = requests.get(f"https://teradownloader.com/download?l={encoded_url}", headers=headers)
    print("Page status:", res.status_code)
    
    # Actually, teradownloader.com uses an API endpoint: https://teraboxvideodownloader.com/api/get-download
    # Wait, the user linked teradownloader.com. Let's look for fastdl link in the HTML
    soup = BeautifulSoup(res.text, 'html.parser')
    links = soup.find_all('a')
    for a in links:
        href = a.get('href', '')
        if 'fastdl' in href or 'data=' in href:
            print("Found download link:", href)
except Exception as e:
    print("Error:", e)
