import os
import re
import base64
import requests
import gemini_service  # Обединеният Gemini модул

def get_issue_and_comments(repo, issue_number, token):
    """Изтегля основното съобщение и всички коментари от GitHub Issue."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    
    # 1. Взимаме Issue информацията
    issue_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    issue_res = requests.get(issue_url, headers=headers)
    if issue_res.status_code != 200:
        raise Exception(f"Грешка при изтегляне на Issue: {issue_res.status_code}")
    issue_data = issue_res.json()

    # 2. Взимаме коментарите
    comments_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    comments_res = requests.get(comments_url, headers=headers)
    if comments_res.status_code != 200:
        raise Exception(f"Грешка при изтегляне на коментари: {comments_res.status_code}")
    comments_data = comments_res.json()

    return issue_data, comments_data

def download_attachment_as_base64(file_url, token):
    """Сваля прикачен файл от GitHub и го връща като base64 и MIME тип."""
    headers = {
        'Authorization': f"Bearer {token}",
        'User-Agent': 'GitHub-Actions-Bot'
    }
    response = requests.get(file_url, headers=headers, allow_redirects=True)
    if response.status_code != 200:
        raise Exception(f"HTTP error! status: {response.status_code}")
    
    array_buffer = response.content
    base64_data = base64.b64encode(array_buffer).decode('utf-8')

    mime_type = "image/jpeg"
    if '.png' in file_url:
        mime_type = "image/png"
    elif '.webp' in file_url:
        mime_type = "image/webp"
    elif '.pdf' in file_url:
        mime_type = "application/pdf"

    return base64_data, mime_type

def post_github_comment(repo, issue_number, token, body):
    """Публикува отговор обратно в GitHub Issue."""
    url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    response = requests.post(url, json={"body": body}, headers=headers)
    if response.status_code == 201:
        print("Успешно публикуван коментар в GitHub.")
    else:
        print(f"Грешка при публикуване в GitHub API: {response.status_code} - {response.text}")

def main():
    repo = os.getenv("REPOSITORY")
    issue_number = os.getenv("ISSUE_NUMBER")
    token = os.getenv("GITHUB_TOKEN")
    event_name = os.getenv("EVENT_NAME")
    
    comment_body = os.getenv("COMMENT_BODY") or ""
    
    if not repo or not issue_number or not token:
        print("Липсват основни системни променливи за GitHub.")
        return

    print(f"Анализирам събитие: {event_name} за Issue #{issue_number}")

    try:
        # Изтегляме историята от GitHub
        issue_data, comments_data = get_issue_and_comments(repo, issue_number, token)
        
        issue_title = issue_data.get("title", "Без заглавие")
        issue_body = issue_data.get("body", "Здравей")

        # Подготвяме масива contents за Gemini
        contents = []
        contents.append({
            "role": "user",
            "parts": [{"text": f'Контекст на разговора: заглавието на това Issue е "{issue_title}". Първоначално запитване: {issue_body}'}]
        })

        # Добавяме предишните коментари като история
        for comment in comments_data:
            user_type = comment.get("user", {}).get("type", "User")
            role = "model" if user_type == "Bot" else "user"
            contents.append({
                "role": role,
                "parts": [{"text": comment.get("body", "")}]
            })

        # Обработваме най-новото съобщение / коментар
        latest_body = comment_body.strip() if event_name == "issue_comment" else issue_body.strip()
        latest_parts = [{"text": latest_body}]

        # Търсим линкове към файлове/изображения в последния текст
        file_urls = re.findall(r'https:\/\/github\.com\/user-attachments\/assets\/[a-zA-Z0-9-]+', latest_body)
        
        debug_log = "\n\n--- [ДЕБЪГ ЛОГ] ---\n"
        if file_urls:
            debug_log += f"Намерени пълни линкове: {len(file_urls)}\n"
            for file_url in file_urls:
                try:
                    print(f"Теглене на прикачен файл: {file_url}")
                    base64_data, mime_type = download_attachment_as_base64(file_url, token)
                    
                    # ПРАВИЛЕН СИНТАКСИС В PYTHON:
                    latest_parts.append({
                        "inline_data": {
                            "data": base64_data,
                            "mime_type": mime_type
                        }
                    })
                    debug_log += f"Успешно добавен файл: {file_url}\n"
                except Exception as err:
                    debug_log += f"ГРЕШКА при теглене на файл: {str(err)}\n"
        else:
            debug_log += "Няма намерени линкове към файлове.\n"

        # Добавяме последното съобщение (с евентуалните файлове към него) в историята
        contents.append({
            "role": "user",
            "parts": latest_parts
        })

        # Извикваме Gemini сервиза
        ai_response = gemini_service.generate_response(contents)
        
        # Добавяме дебъг лога към отговора
        final_output = ai_response + debug_log

        # Връщаме отговора в GitHub
        post_github_comment(repo, issue_number, token, final_output)

    exceptException as e:
        error_message = f"Възникна грешка в модулната система:\n```\n{str(e)}\n```"
        print(error_message)
        post_github_comment(repo, issue_number, token, error_message)

if __name__ == "__main__":
    main()
