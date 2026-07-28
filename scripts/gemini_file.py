import os
import google.generativeai as genai

def process_file(prompt):
    """
    Обработва заявки, свързани с файлове или изображения с Gemini.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Грешка: GEMINI_API_KEY не е намерен в променливите на средата.")

    # Конфигуриране на API ключа
    genai.configure(api_key=api_key)

    # Запазваме твоя избран модел
    model_name = "gemini-3.5-flash-lite"

    try:
        print(f"Извиквам Gemini File Module с модел: {model_name}")
        
        # Тук може да се добави логика за качване на истински файлове, 
        # ако в бъдеще изтегляш прикачен файл от GitHub.
        # Засега изпращаме заявката към модела с текст, указващ работа с файл.
        
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(f"Обработи следната заявка свързана с файл: {prompt}")

        if response and response.text:
            return response.text
        else:
            return "Gemini File Module върна празен отговор."

    except Exception as e:
        error_msg = f"Грешка при връзка с Gemini (File): {str(e)}"
        print(error_msg)
        raise Exception(error_msg)
