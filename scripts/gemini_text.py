import os
import google.generativeai as genai

def generate_text(prompt):
    """
    Генерира текстов отговор с Gemini на базата на подаден промпт.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Грешка: GEMINI_API_KEY не е намерен в променливите на средата.")

    # Конфигуриране на API ключа
    genai.configure(api_key=api_key)

    # Запазваме твоя избран модел
    model_name = "gemini-3.5-flash-lite"  # (Или името, което си задал в репозиторието)

    try:
        print(f"Извиквам Gemini Text Module с модел: {model_name}")
        
        # Създаване на инстанция на модела и генериране на съдържание
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)

        if response and response.text:
            return response.text
        else:
            return "Gemini върна празен отговор."

    except Exception as e:
        error_msg = f"Грешка при връзка с Gemini (Text): {str(e)}"
        print(error_msg)
        raise Exception(error_msg)
