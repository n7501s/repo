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
    Ти водиш диалог с разработчика в GitHub Issue и управляваш документацията (README.md).
    
    Когато в рамките на разговора се вземат решения, обсъждат се нови идеи (като Roadmap, приложени функции или отхвърлени неща), 
    ти имаш пълен свободен достъп да редактираш, добавяш или премахваш съдържание от README.md, за да го поддържаш перфектно структурирано и актуално.
    
    Ако има нужда от промяна в документацията, в края на отговора си задължително върни цялото ново съдържание на README.md (или поне актуалните секции) в следния скрит блок:
    [README_FULL_UPDATE]
    Тук пиши целия актуален текст на README.md или съответните секции, които да заменят старите...
    [/README_FULL_UPDATE]
    
    Ако няма нужда от промени, не слагай този блок.
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
