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
    """
    Обновява README.md в бранча 'dev' на базата на JSON данни от Gemini.
    Поддържа add_idea, add_implemented, add_rejected и remove_item.
    """
    action = update_data.get("action")
    items = update_data.get("items", [])
    path = "README.md"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    
    try:
        file_content = get_github_file_content(repo, path, "dev", token)
    except Exception as e:
        print(f"Грешка при четене на README.md: {e}")
        return

    lines = file_content.splitlines()
    new_lines = []
    
    section_headers = {
        "add_idea": "## 🚀 Ideas & Roadmap",
        "add_implemented": "## ✅ Current Features",
        "add_rejected": "## ❌ Archived / Rejected Ideas",
        "remove_item": "## 🚀 Ideas & Roadmap"
    }
    
    target_header = section_headers.get(action, "## 🚀 Ideas & Roadmap")
    is_in_target = False
    
    # Логика за премахване на елемент (премахва съвпадението независимо в коя секция е)
    if action == "remove_item":
        for line in lines:
            if line.startswith("## "):
                new_lines.append(line)
                continue
            
            # Търси и трие съвпадението навсякъде в README-то (и в Ideas, и в Rejected)
            should_remove = any(item.lower() in line.lower() for item in items)
            if should_remove:
                print(f"Премахвам от README: {line.strip()}")
                continue
            
            new_lines.append(line)
    else:
        # Логика за добавяне
        added = False
        for line in lines:
            new_lines.append(line)
            if line.strip() == target_header and not added:
                for item in items:
                    formatted_item = f"- {item}"
                    if formatted_item not in file_content:
                        new_lines.append(formatted_item)
                added = True

    updated_content = "\n".join(new_lines) + "\n"
    
    # Взимаме SHA за обновяване чрез PyGithub или REST API
    # Тъй като ползваш requests в целия скрипт, ето го чисто през requests:
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    # Първо взимаме актуалния sha на файла
    get_res = requests.get(f"{url}?ref=dev", headers=headers)
    if get_res.status_code != 200:
        print(f"Грешка при взимане на SHA за README.md: {get_res.status_code}")
        return
    sha = get_res.json().get("sha")
    
    # Кодираме съдържанието в base64 за GitHub API
    content_encoded = base64.b64encode(updated_content.encode('utf-8')).decode('utf-8')
    
    payload = {
        "message": f"System Architect: update README via action {action}",
        "content": content_encoded,
        "sha": sha,
        "branch": "dev"
    }
    
    put_res = requests.put(url, json=payload, headers=headers)
    if put_res.status_code in [200, 201]:
        print("README.md е успешно обновен!")
    else:
        print(f"Грешка при обновяване на README.md: {put_res.status_code} - {put_res.text}")

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

def fetch_web_page_content(url):
    """Изтегля уеб страница и извлича текстовото съдържание (премахва HTML таговете)."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (GitHub-Actions-Bot)'
    }
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
        raise Exception(f"HTTP error! status: {response.status_code}")
    
    html_content = response.text
    
    # Премахваме скриптове, стилове и HTML тагове с регулярни изрази
    clean_text = re.sub(r'<script.*?>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    clean_text = re.sub(r'<style.*?>.*?</style>', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
    clean_text = re.sub(r'<[^>]+>', ' ', clean_text) # Махаме таговете
    clean_text = re.sub(r'\s+', ' ', clean_text).strip() # Събираме празни пространства
    
    # Връщаме първите 5000 символа, за да не препълваме контекста на Gemini
    return clean_text[:5000]

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
        github_file_urls = re.findall(r'https:\/\/github\.com\/([^/]+\/[^/]+)\/blob\/([^/]+)\/(.+)', latest_body)
        # Търсим външни уеб линкове (като изключваме github.com)
        web_urls = re.findall(r'https?:\/\/(?!github\.com)[^\s]+', latest_body)

        
        # Инициализираме лога само веднъж тук!
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

        # 2. Обработка на линкове към стари Issue-та
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

                # 4. Обработка на външни уеб линкове (Новата функционалност)
        if web_urls:
            debug_log += f"Намерени външни линкове: {len(web_urls)}\n"
            for web_url in web_urls:
                try:
                    page_text = fetch_web_page_content(web_url)
                    latest_parts.append({
                        "text": f"\n[Съдържание от уеб страница '{web_url}']: \n{page_text}\n"
                    })
                    debug_log += f"Успешно прочетена уеб страница: {web_url}\n"
                except Exception as err:
                    debug_log += f"ГРЕШКА при четене на уеб страница {web_url}: {str(err)}\n"
                
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
