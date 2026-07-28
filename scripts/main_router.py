import os
import sys
import requests
import gemini_text
import gemini_file

def post_github_comment(repo, issue_number, token, body):
    """Публикува коментар обратно в GitHub Issue."""
    if not issue_number or not token or not repo:
        print("Липсват данни за връзка с GitHub (repo, issue_number или token).")
        return
    
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
    # Четене на променливите от средата (подадени от YAML)
    repo = os.getenv("REPOSITORY")
    issue_number = os.getenv("ISSUE_NUMBER")
    token = os.getenv("GITHUB_TOKEN")
    event_name = os.getenv("EVENT_NAME")
    
    # Взимаме текста на събитието (коментар или описание на issue)
    comment_body = os.getenv("COMMENT_BODY") or ""
    issue_body = os.getenv("ISSUE_BODY") or ""
    
    # Определяме актуален текст за обработка
    prompt_text = comment_body.strip() if event_name == "issue_comment" else issue_body.strip()
    
    print(f"Анализирам събитие: {event_name} за Issue #{issue_number}")
    
    if not prompt_text:
        print("Няма текст за обработка.")
        return

    ai_response = ""

    try:
        # ПРИМЕРНА ЛОГИКА ЗА РУТИРАНЕ:
        # Проверяваме дали в текста се споменава файл/картинка или има линк към изображение
        if "file" in prompt_text.lower() or "image" in prompt_text.lower() or "снимка" in prompt_text.lower() or "файл" in prompt_text.lower():
            print("Маршрут: Извиквам Gemini File Module.")
            # Тук може да подадеш и конкретен път към файл, ако е бил качен
            ai_response = gemini_file.process_file(prompt_text)
        else:
            print("Маршрут: Извиквам Gemini Text Module.")
            ai_response = gemini_text.generate_text(prompt_text)

    except Exception as e:
        ai_response = f"Възникна грешка при изпълнение на AI модула:\n```\n{str(e)}\n```"
        print(ai_response)

    # Връщаме отговора обратно в GitHub Issue
    if ai_response and repo and issue_number:
        post_github_comment(repo, issue_number, token, ai_response)
    else:
        print("Няма отговор за връщане или липсват параметри за GitHub.")

if __name__ == "__main__":
    main()
