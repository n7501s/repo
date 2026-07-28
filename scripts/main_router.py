import os
import re

# Импортираме нашите модули
import gemini_text
import gemini_file


def has_files(text):
  # Проверява дали в текста има линкове към картинки или файлове (например от GitHub markdown)
  # Или ако имаме специален маркец за файл
  image_extensions = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".txt")
  if any(ext in text.lower() for ext in image_extensions):
    return True
  return False


def main():
  issue_body = os.environ.get("ISSUE_BODY", "")
  issue_title = os.environ.get("ISSUE_TITLE", "")
  # Събираме заглавие и съдържание за анализ
  full_content = f"{issue_title}\n{issue_body}"

  print(f"Анализирам съобщението: {issue_title}")

  # РУТИРАНЕ: Ако има файл/картинка, пращаме към файловия модул. Иначе към текстовия.
  if has_files(full_content):
    print(">>> Засечен файл или изображение! Извиквам Gemini File Module.")
    gemini_file.process_file_request(full_content)
  else:
    print(">>> Само текст. Извиквам Gemini Text Module.")
    gemini_text.process_text_request(full_content)


if __name__ == "__main__":
  main()
