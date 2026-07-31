import os
import requests
import base64
from bs4 import BeautifulSoup

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = os.getenv("GITHUB_REPOSITORY")

def get_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

def get_issue_and_comments(issue_number):
    url = f"https://api.github.com/repos/{REPO_NAME}/issues/{issue_number}"
    response = requests.get(url, headers=get_headers())
    if response.status_code != 200:
        raise Exception(f"Failed to fetch issue: {response.status_code} - {response.text}")
    
    issue_data = response.json()
    comments_url = issue_data.get("comments_url")
    comments_response = requests.get(comments_url, headers=get_headers())
    
    comments = comments_response.json() if comments_response.status_code == 200 else []
    return issue_data, comments

def download_attachment_as_base64(url):
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"} if "githubusercontent.com" in url else {}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', 'application/octet-stream')
            encoded = base64.b64encode(response.content).decode('utf-8')
            return {"mime_type": content_type, "data": encoded}
    except Exception as e:
        print(f"Error downloading attachment {url}: {e}")
    return None

def post_github_comment(issue_number, body):
    url = f"https://api.github.com/repos/{REPO_NAME}/issues/{issue_number}/comments"
    response = requests.post(url, headers=get_headers(), json={"body": body})
    return response.status_code == 201

def update_readme_via_github_api(new_content, commit_message="Update README via automated script"):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/README.md"
    response = requests.get(url, headers=get_headers())
    if response.status_code != 200:
        print(f"Failed to fetch README for update: {response.status_code}")
        return False
    
    sha = response.json().get("sha")
    encoded_content = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
    
    data = {
        "message": commit_message,
        "content": encoded_content,
        "sha": sha,
        "branch": os.getenv("GITHUB_REF_NAME", "main")
    }
    
    put_response = requests.put(url, headers=get_headers(), json=data)
    return put_response.status_code in [200, 201]

def get_github_file_content(path):
    url = f"https://api.github.com/repos/{REPO_NAME}/contents/{path}"
    response = requests.get(url, headers=get_headers())
    if response.status_code == 200:
        file_data = response.json()
        return base64.b64decode(file_data.get("content", "")).decode('utf-8')
    return None
