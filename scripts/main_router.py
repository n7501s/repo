import os
import sys
from github_client import (
    get_issue_and_comments, 
    post_github_comment, 
    update_readme_via_github_api
)
from chatgpt_analyzer import load_progress, save_progress
from model_provider import DynamicModelProvider

def main():
    print("Starting Main Router (Autonomous Architecture)...")
    issue_number = os.getenv("ISSUE_NUMBER")
    if not issue_number:
        print("No ISSUE_NUMBER provided in environment.")
        return

    try:
        issue_data, comments = get_issue_and_comments(issue_number)
        print(f"Successfully fetched issue #{issue_number} with {len(comments)} comments.")
        
        # Зареждане на състоянието
        state = load_progress()
        
        # Инициализиране на автономния доставчик на модели (Без ръчни ключове)
        ai_provider = DynamicModelProvider()
        
        # Тест на автономното генериране
        test_prompt = f"Analyze issue #{issue_number} and determine next steps."
        ai_response = ai_provider.generate_response(test_prompt)
        print(ai_response)
        
        print("Step 2 completed: Dynamic model provisioning implemented successfully.")
        
    except Exception as e:
        print(f"Critical error in main router execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
