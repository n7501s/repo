import os
import sys
from github_client import (
    get_issue_and_comments, 
    post_github_comment, 
    update_readme_via_github_api
)
from chatgpt_analyzer import load_progress, save_progress

def main():
    print("Starting Main Router (Modular Architecture)...")
    issue_number = os.getenv("ISSUE_NUMBER")
    if not issue_number:
        print("No ISSUE_NUMBER provided in environment.")
        return

    try:
        issue_data, comments = get_issue_and_comments(issue_number)
        print(f"Successfully fetched issue #{issue_number} with {len(comments)} comments.")
        
        # Зареждане на състоянието
        state = load_progress()
        
        # Тук ще надградим динамичния механизъм за моделите в следващата стъпка
        print("Modular separation step completed successfully.")
        
    except Exception as e:
        print(f"Critical error in main router execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
