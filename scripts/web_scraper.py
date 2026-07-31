import requests
from bs4 import BeautifulSoup

def fetch_web_page_content(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for script in soup(["script", "style"]):
                script.extract()
            text = soup.get_text(separator=' ', strip=True)
            return text
    except Exception as e:
        print(f"Error fetching web page {url}: {e}")
    return None
