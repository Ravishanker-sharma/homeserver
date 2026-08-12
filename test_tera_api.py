import requests
from bs4 import BeautifulSoup
import re

url = "https://www.1024tera.com/sharing/link?surl=uOH1rigHDKBaNt01_NEQPg"
headers = {'User-Agent': 'Mozilla/5.0'}

res = requests.get(f"https://teradownloader.com/download?l={requests.utils.quote(url)}", headers=headers)
html = res.text

# Let's see if there's any JSON or API endpoint mentioned
print("Matches for 'api' or 'fetch':")
for line in html.split('\n'):
    if 'api' in line.lower() or 'fetch' in line.lower() or 'fastdl' in line.lower():
        print(line.strip()[:200])

