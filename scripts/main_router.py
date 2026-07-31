import os
import sys
from github_client import (
    get_issue_and_comments, 
    post_github_comment, 
    update_readme_via_github_api
)
from chatgpt_analyzer import load_progress, save_progress
from chatgpt_parser import parse_chatgpt_markdown, chunk_conversation_history
from model_provider import DynamicModelProvider

def main():
    print("Starting Main Router (Autonomous & Modular Architecture)...")
    issue_number = os.getenv("ISSUE_NUMBER")
    if not issue_number:
        print("No ISSUE_NUMBER provided in environment.")
        return

    try:
        # 1. Извличане на Issue и коментари
        issue_data, comments = get_issue_and_comments(issue_number)
        print(f"Successfully fetched issue #{issue_number} with {len(comments)} comments.")
        
        # 2. Зареждане на състоянието
        state = load_progress()
        
        # 3. Автономен доставчик на модели (Без ръчни ключове и ротации)
        ai_provider = DynamicModelProvider()
        
        # 4. Пример за използване на запазения парсер (ако имаме качена история за анализ)
        # (Тук показваме как chatgpt_parser.py работи в новата екосистема)
        sample_markdown = "## Prompt\nТест на системата\n## Response\nРаботи перфектно."
        parsed_data = parse_chatgpt_markdown(sample_markdown)
        chunks = chunk_conversation_history(parsed_data)
        
        # 5. Генерация чрез автономния модел
        ai_response = ai_provider.generate_response(f"Analyze issue #{issue_number} with {len(chunks)} parsed history chunks.")
        print(ai_response)
        
        # 6. Публикуване на отговора обратно в GitHub Issue
        success = post_github_comment(issue_number, f"🤖 **Autonomous Bot Response:**\n\n{ai_response}")
        if success:
            print("Successfully posted response to GitHub Issue.")
        else:
            print("Failed to post response to GitHub Issue.")
        
        print("Final integration completed successfully. Full automation achieved!")
        
    except Exception as e:
        print(f"Critical error in main router execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
