import os
import google.generativeai as genai
import requests


def post_comment(message):
  token = os.environ.get("GITHUB_TOKEN")
  repo = os.environ.get("GITHUB_REPOSITORY")
  issue_number = os.environ.get("ISSUE_NUMBER")

  url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
  headers = {
      "Authorization": f"Bearer {token}",
      "Accept": "application/vnd.github+json",
  }
  response = requests.post(url, json={"body": message}, headers=headers)
  print(f"GitHub API Response: {response.status_code}")


def process_text_request(prompt):
  # Търсим ключа в двете възможни системни променливи
  api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
  
  if not api_key:
    post_comment("Грешка: API ключът за Gemini липсва в системите на GitHub Secrets!")
    return

  genai.configure(api_key=api_key)

  model = genai.GenerativeModel("gemini-3.5-flash-lite")

  try:
    response = model.generate_content(prompt)
    answer = response.text
  except Exception as e:
    answer = f"Грешка при връзка с Gemini (Text): {str(e)}"

  post_comment(answer)
