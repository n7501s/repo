import json
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

def update_readme_via_github_api(repo, token, update_data):
    """Тегли README.md, добавя новите идеи/задачи в съответната секция и я връща с commit/push в dev бранча."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    file_url = f"https://api.github.com/repos/{repo}/contents/README.md"
    
    res = requests.get(file_url, headers=headers)
    if res.status_code != 200:
        print(f"Грешка при четене на README.md: {res.status_code}")
        return
    
    file_info = res.json()
    sha = file_info["sha"]
    content_encoded = file_info["content"]
    current_content = base64.b64decode(content_encoded).decode('utf-8')

    action = update_data.get("action")
    items = update_data.get("items", []) # Очакваме списък от идеи/задачи (items)

    target_header = ""
    if action == "add_idea":
        target_header = "## 🚀 Ideas & Roadmap"
    elif action == "add_implemented":
        target_header = "## ✅ Current Features"
    elif action == "add_rejected":
        target_header = "## ❌ Archived / Rejected Ideas"

    if target_header and target_header in current_content and items:
        # Генерираме новите редове за списъка
        new_lines_str = ""
        for item in items:
            new_line = f"- {item}"
            if new_line not in current_content:
                new_lines_str += f"\n{new_line}"

        if new_lines_str:
            # Добавяме новите редове точно след заглавието
            current_content = current_content.replace(target_header, f"{target_header}{new_lines_str}")
            
            updated_content_encoded = base64.b64encode(current_content.encode('utf-8')).decode('utf-8')
            commit_data = {
                "message": f"🤖 Auto-update README: Добавени нови идеи/задачи",
                "content": updated_content_encoded,
                "sha": sha,
                "branch": "dev"
            }
            
            put_res = requests.put(file_url, json=commit_data, headers=headers)
            if put_res.status_code in [200, 201]:
                print("Успешно авто-обновено README.md с множество идеи в dev бранча!")
            else:
                print(f"Грешка при запис на README.md: {put_res.status_code} - {put_res.text}")

def get_github_file_content(repo, file_path, branch, token):
    """Изтегля съдържанието на файл от GitHub репозиторий по даден път и бранч."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={branch}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Грешка при четене на файл {file_path}: {response.status_code}")
    
    file_info = response.json()
    content_encoded = file_info["content"]
    file_content = base64.b64decode(content_encoded).decode('utf-8')
    return file_content

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

        # Търсим различни видове линкове в последния текст
        file_urls = re.findall(r'https:\/\/github\.com\/user-attachments\/assets\/[a-zA-Z0-9-]+', latest_body)
        github_issue_urls = re.findall(r'https:\/\/github\.com\/([^/]+\/[^/]+)\/issues\/(\d+)', latest_body)
        # Търсим линкове към файлове в GitHub (напр. .../blob/dev/path/to/file)
        github_file_urls = re.findall(r'https:\/\/github\.com\/([^/]+\/[^/]+)\/blob\/([^/]+)\/(.+)', latest_body)
        
        debug_log = "\n\n--- [ДЕБЪГ ЛОГ] ---\n"
        
        # 1. Обработка на прикачени изображения/файлове
        if file_urls:
            debug_log += f"Намерени пълни линкове: {len(file_urls)}\n"
            for file_url in file_urls:
                try:
                    print(f"Теглене на прикачен файл: {file_url}")
                    base64_data, mime_type = download_attachment_as_base64(file_url, token)
                    
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

        # 2. Обработка на линкове към стари Issue-та (Новата функционалност)
        if github_issue_urls:
            debug_log += f"Намерени линкове към Issue-та: {len(github_issue_urls)}\n"
            for repo_path, issue_num in github_issue_urls:
                try:
                    iss_data, _ = get_issue_and_comments(repo_path, issue_num, token)
                    iss_title = iss_data.get("title", "")
                    iss_body = iss_data.get("body", "")
                    latest_parts.append({
                        "text": f"\n[Контекст от свързано Issue #{issue_num} - Заглавие: '{iss_title}']: \n{iss_body}\n"
                    })
                    debug_log += f"Успешно зареден контекст от Issue #{issue_num}\n"
                except Exception as err:
                    debug_log += f"ГРЕШКА при четене на Issue #{issue_num}: {str(err)}\n"

        # 3. Обработка на линкове към файлове в GitHub
        if github_file_urls:
            debug_log += f"Намерени линкове към GitHub файлове: {len(github_file_urls)}\n"
            for repo_path, branch, file_path in github_file_urls:
                try:
                    file_content = get_github_file_content(repo_path, file_path, branch, token)
                    latest_parts.append({
                        "text": f"\n[Съдържание на файл '{file_path}' от бранч '{branch}']: \n```python\n{file_content}\n```\n"
                    })
                    debug_log += f"Успешно зареден файл: {file_path} (бранч: {branch})\n"
                except Exception as err:
                    debug_log += f"ГРЕШКА при четене на файл {file_path}: {str(err)}\n"
        
        debug_log = "\n\n--- [ДЕБЪГ ЛОГ] ---\n"
        if file_urls:
            debug_log += f"Намерени пълни линкове: {len(file_urls)}\n"
            for file_url in file_urls:
                try:
                    print(f"Теглене на прикачен файл: {file_url}")
                    base64_data, mime_type = download_attachment_as_base64(file_url, token)
                    
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
        
        # Търсим дали Gemini е решил да обнови README с [README_UPDATE]
        readme_update_match = re.search(r'\[README_UPDATE\](.*?)\[/README_UPDATE\]', ai_response, dak_flags := re.DOTALL)
        if readme_update_match:
            try:
                json_str = readme_update_match.group(1).strip()
                update_data = json.loads(json_str)
                print(f"Засечена заявка за README ъпдейт с действие: {update_data.get('action')}")
                update_readme_via_github_api(repo, token, update_data)
            except Exception as ex:
                print(f"Грешка при обработка на README_UPDATE: {str(ex)}")
            
            # Премахваме скрития блок от коментара, за да не се показва в GitHub Issue-то
            ai_response = re.sub(r'\[README_UPDATE\].*?\[/README_UPDATE\]', '', ai_response, flags=re.DOTALL).strip()

        # Добавяме дебъг лога към отговора
        final_output = ai_response + debug_log

        # Връщаме отговора в GitHub
        post_github_comment(repo, issue_number, token, final_output)

    except Exception as e:
        error_message = f"Възникна грешка в модулната система:\n```\n{str(e)}\n```"
        print(error_message)
        post_github_comment(repo, issue_number, token, error_message)

if __name__ == "__main__":
    main()
