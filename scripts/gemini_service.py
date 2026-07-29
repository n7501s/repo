import os
from google import genai
from google.genai import types

def generate_response(contents_history):
    """
    Универсална функция за връзка с Gemini, приемаща пълната история (текст + изображения).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Грешка: GEMINI_API_KEY не е намерен в променливите на средата.")

    # Инициализираме новия GoogleGenAI клиент
    client = genai.Client(api_key=api_key)
    model_name = "gemini-3.5-flash-lite"  # <--- ЗАПАЗЕН ТВОЯТ МОДЕЛ

    # Системна инструкция за автономния агент
    system_instruction = """
    Ти си интелигентен AI асистент и системен архитект на този проект. 
    Ти водиш диалог с разработчика в GitHub Issue. Без да чакаш специални команди, ти сам преценяваш от контекста на разговора кога да актуализираш документацията.
    
    Следиш контекста за:
    1. Нови идеи за подобрения или Roadmap -> действие: "add_idea" (отива в ## 🚀 Ideas & Roadmap)
    2. Приложени и завършени функции -> действие: "add_implemented" (отива в ## ✅ Current Features)
    3. Отхвърлени идеи с причините за тях -> действие: "add_rejected" (отива в ## ❌ Archived / Rejected Ideas)
    
    Когато се вземе решение за промяна, в края на своя отговор задължително добавяй скрит блок в точно този JSON формат:
    [README_UPDATE]
    {"action": "add_implemented", "items": ["Име на новата функция тук"]}
    [/README_UPDATE]
    
    Ако в разговора няма нищо ново за добавяне в документацията, НЕ слагай този блок.
    """

    try:
        print(f"Извиквам Gemini с модел: {model_name}")
        
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
        )

        response = client.models.generate_content(
            model=model_name,
            contents=contents_history,
            config=config
        )

        if response and response.text:
            return response.text
        else:
            return "Gemini върна празен отговор."

    except Exception as e:
        error_msg = f"Грешка при връзка с Gemini: {str(e)}"
        print(error_msg)
        raise Exception(error_msg)
