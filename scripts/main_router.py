import json
import os
import re
import base64
import requests
import gemini_service  # Обединеният Gemini модул с ротация на ключове
from chatgpt_parser import parse_chatgpt_markdown, chunk_conversation_history

STATE_FILE = ".chatgpt_progress.json"

def load_progress():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"completed_chunks": [], "insights": []}
    return {"completed_chunks": [], "insights": []}

def save_progress(completed_chunks, insights):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"completed_chunks": completed_chunks, "insights": insights}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Грешка при запис на прогреса: {e}")

def get_issue_and_comments(repo, issue_number, token):
    """Изтегля основното съобщение и всички коментари от GitHub Issue."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    
    issue_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
    issue_res = requests.get(issue_url, headers=headers)
    if issue_res.status_code != 200:
        raise Exception(f"Грешка при изтегляне на Issue: {issue_res.status_code}")
    issue_data = issue_res.json()

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
    """Обновява README.md в бранча 'dev' на базата на JSON данни от Gemini."""
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
    
    if action == "remove_item":
        for line in lines:
            if line.startswith("## "):
                new_lines.append(line)
                continue
            should_remove = any(item.lower() in line.lower() for item in items)
            if should_remove:
                print(f"Премахвам от README: {line.strip()}")
                continue
            new_lines.append(line)
    else:
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
    
    url = f"https://api.github.com/repos/{repo}/contents/{path}"
    get_res = requests.get(f"{url}?ref=dev", headers=headers)
    if get_res.status_code != 200:
        print(f"Грешка при взимане на SHA за README.md: {get_res.status_code}")
        return
    sha = get_res.json().get("sha")
    
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
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (GitHub-Actions-Bot)'
    }
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
        raise Exception(f"HTTP error! status: {response.status_code}")
    
    html_content = response.text
    clean_text = re.sub(r'<script.*?>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    clean_text = re.sub(r'<style.*?>.*?</style>', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
    clean_text = re.sub(r'<[^>]+>', ' ', clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text[:5000]

def process_large_chatgpt_history(file_path: str):
    """
    Чете големия ChatGPT файл от репозиторито, парсира го 
    и го разделя с интелигентни динамични парчета.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        parsed_data = parse_chatgpt_markdown(content)
        print(f"Успешно парсирани {len(parsed_data)} диалога от ChatGPT историята.")
        
        # Използваме новата функция с динамичен размер на парчетата (max_chunk_size=None по подразбиране)
        chunks = chunk_conversation_history(parsed_data)
        print(f"Файлът е разделен на {len(chunks)} интелигентни парчета.")
        return chunks
    except Exception as e:
        print(f"Грешка при обработка на ChatGPT историята: {e}")
        return []

def analyze_chatgpt_chunks_with_gemini(chunks):
    """
    Обхожда парчетата с поддръжка на запазване на състоянието (Resume on Failure)
    и автоматична ротация на ключове през gemini_service.
    """
    state = load_progress()
    completed_chunks = state.get("completed_chunks", [])
    extracted_insights = state.get("insights", [])
    
    print(f"Стартиране на анализ с Gemini. Общо парчета: {len(chunks)}. Вече обработени: {len(completed_chunks)}.")
    
    for i, chunk in enumerate(chunks):
        if i in completed_chunks:
            continue
            
        print(f"Анализиране на парче {i+1} от {len(chunks)}...")
        
        contents = [
            {
                "role": "user",
                "parts": [{
                    "text": (
                        "Ти си системен архитект. Анализирай следния откъс от история на чат с разработчик "
                        "и извлечи накратко (ако има такива) нови идеи за подобрения, Roadmap точки или завършени функции. "
                        "Върни ги в кратки точки. Ако няма нищо съществено в този откъс, отговори само с 'НЯМА'.\n\n"
                        f"ОТКЪС:\n{chunk}"
                    )
                }]
            }
        ]
        
        try:
            # Извикваме generate_response (или call_gemini_api), което вече има ротация на ключове
            response = gemini_service.generate_response(contents)
            if response and "НЯМА" not in response.upper():
                extracted_insights.append(response)
            
            completed_chunks.append(i)
            save_progress(completed_chunks, extracted_insights)
            
        except Exception as e:
            print(f"Грешка при анализ на парче {i+1}: {e}")
            print("Запазваме текущия прогрес и прекъсваме безопасно за следващ тригер.")
            break
            
    return extracted_insights

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
        issue_data, comments_data = get_issue_and_comments(repo, issue_number, token)
        issue_title = issue_data.get("title", "Без заглавие")
        issue_body = issue_data.get("body", "Здравей")

        contents = []
        contents.append({
            "role": "user",
            "parts": [{"text": f'Контекст на разговора: заглавието на това Issue е "{issue_title}". Първоначално запитване: {issue_body}'}]
        })

        for comment in comments_data:
            user_type = comment.get("user", {}).get("type", "User")
            role = "model" if user_type == "Bot" else "user"
            contents.append({
                "role": role,
                "parts": [{"text": comment.get("body", "")}]
            })

        latest_body = comment_body.strip() if event_name == "issue_comment" else issue_body.strip()
        latest_parts = [{"text": latest_body}]

        file_urls = re.findall(r'https:\/\/github\.com\/user-attachments\/assets\/[a-zA-Z0-9-]+', latest_body)
        github_issue_urls = re.findall(r'https:\/\/github\.com\/([^/]+\/[^/]+)\/issues\/(\d+)', latest_body)
        github_file_urls = re.findall(r'https:\/\/github\.com\/([^/]+\/[^/]+)\/blob\/([^/]+)\/(.+)', latest_body)
        web_urls = re.findall(r'https?:\/\/(?!github\.com)[^\s]+', latest_body)

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

        if "chatgpt_history.md" in latest_body.lower() or "история" in latest_body.lower():
            try:
                print("Засечено заявка за анализ на ChatGPT историята...")
                chunks = process_large_chatgpt_history("data/chatgpt_history.md")
                if chunks:
                    insights = analyze_chatgpt_chunks_with_gemini(chunks)
                    if insights:
                        insight_text = "\n\n**Извлечени идеи от ChatGPT историята:**\n" + "\n".join(insights)
                        latest_parts.append({"text": insight_text})
                        debug_log += f"Успешно анализирани и извлечени идеи от {len(chunks)} парчета.\n"
            except Exception as hist_err:
                debug_log += f"ГРЕШКА при анализ на ChatGPT историята: {str(hist_err)}\n"

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
                
        contents.append({
            "role": "user",
            "parts": latest_parts
        })

        ai_response = gemini_service.generate_response(contents)
        
        readme_update_match = re.search(r'\[README_UPDATE\](.*?)\[/README_UPDATE\]', ai_response, re.DOTALL)
        if readme_update_match:
            try:
                json_str = readme_update_match.group(1).strip()
                update_data = json.loads(json_str)
                print(f"Засечена заявка за README ъпдейт с действие: {update_data.get('action')}")
                update_readme_via_github_api(repo, token, update_data)
            except Exception as ex:
                print(f"Грешка при обработка на README_UPDATE: {str(ex)}")
            
            ai_response = re.sub(r'\[README_UPDATE\].*?\[/README_UPDATE\]', '', ai_response, flags=re.DOTALL).strip()

        final_output = ai_response + debug_log
        post_github_comment(repo, issue_number, token, final_output)

    except Exception as e:
        error_message = f"Възникна грешка в модулната система:\n```\n{str(e)}\n```"
        print(error_message)
        post_github_comment(repo, issue_number, token, error_message)

if __name__ == "__main__":
    main()
