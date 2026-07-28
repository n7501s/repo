import os
from google import genai
from google.genai import types

def generate_with_media(contents_history):
    """
    Изпраща история на съобщенията (включително текст и base64 изображения/файлове) към Gemini.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Грешка: GEMINI_API_KEY не е намерен в променливите на средата.")

    # Инициализираме новия GoogleGenAI клиент
    client = genai.Client(api_key=api_key)
    model_name = "gemini-3.5-flash-lite"

    try:
        print(f"Извиквам Gemini с модел: {model_name} (с медия/история)")
        
        # Използваме новия SDK формат за генериране на съдържание с пълния контекст
        response = client.models.generate_content(
            model=model_name,
            contents=contents_history,
        )

        if response and response.text:
            return response.text
        else:
            return "Gemini върна празен отговор."

    except Exception as e:
        error_msg = f"Грешка при връзка с Gemini: {str(e)}"
        print(error_msg)
        raise Exception(error_msg)
