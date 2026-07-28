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


def process_file_request(content):
  api_key = os.environ.get("GEMINI_API_KEY")
  genai.configure(api_key=api_key)

  # Тук слагаш твоята работна логика от втория файл за сваляне на файла и подаването му към Gemini
  # За момента слагам примерна структура:
  model = genai.GenerativeModel("gemini-3.5-flash-lite")

  # Тук ще се обработва файла (ще надградим тази част с твоя код за сваляне от линк)
  try:
    response = model.generate_content([
        "Моля анализирай приключения файл/картинка:",
        content,
    ])
    answer = response.text
  except Exception as e:
    answer = f"Грешка при обработка на файл с Gemini: {str(e)}"

  post_comment(answer)
