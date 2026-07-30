import os
import time
from google import genai
from google.genai import types

def get_available_gemini_keys():
    """
    Динамично открива всички налични ключове в GitHub Secrets / Environment Variables
    по шаблон GEMINI_API_KEY_1, GEMINI_API_KEY_2, ... докато има налични.
    Също така проверява и за стандартния GEMINI_API_KEY като резервен вариант.
    """
    keys = []
    i = 1
    while True:
        key_name = f"GEMINI_API_KEY_{i}"
        key_value = os.environ.get(key_name)
        
        if not key_value:
            break
            
        keys.append(key_value)
        i += 1
        
    # Добавяме стандартния GEMINI_API_KEY ако няма номерирани или като допълнение
    standard_key = os.environ.get("GEMINI_API_KEY")
    if standard_key and standard_key not in keys:
        keys.append(standard_key)
        
    return keys

class RotatingGeminiClient:
    def __init__(self):
        self.keys = get_available_gemini_keys()
        if not self.keys:
            print("⚠️ ВНИМАНИЕ: Няма намерени Gemini API ключове в Environment/Secrets!")
        else:
            print(f"🔑 Намерени са {len(self.keys)} Gemini API ключа за ротация.")
        self.current_key_index = 0

    def get_client(self):
        if not self.keys:
            raise ValueError("Грешка: Липсват API ключове за Gemini в променливите на средата.")
        current_key = self.keys[self.current_key_index]
        return genai.Client(api_key=current_key)

    def rotate_key(self):
        if len(self.keys) <= 1:
            return False
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        print(f"⏳ Превключване към следващ API ключ (Индекс: {self.current_key_index + 1}/{len(self.keys)})...")
        return True

# Глобален инстанция на ротатора на ключове
key_rotator = RotatingGeminiClient()

def generate_response(contents_history):
    """
    Универсална функция за връзка с Gemini, приемаща пълната история (текст + изображения),
    със защитен механизъм за автоматична ротация на ключове при грешки/лимити.
    """
    max_retries = max(len(key_rotator.keys), 1) * 2
    attempts = 0
    model_name = "gemini-3.5-flash-lite"

    # Системна инструкция за автономния агент
    system_instruction = """
    Ти си интелигентен AI асистент и системен архитект на този проект. 
    Ти водиш диалог с разработчика в GitHub Issue. Без да чакаш специални команди, ти сам преценяваш от контекста на разговора кога да актуализираш документацията.
    
    Следиш контекста за:
    1. Нови идеи за подобрения или Roadmap -> действие: "add_idea" (отива в ## 🚀 Ideas & Roadmap)
    2. Приложени и завършени функции -> действие: "add_implemented" (отива в ## ✅ Current Features)
    3. Отхвърлени идеи с причините за тях -> действие: "add_rejected" (отива в ## ❌ Archived / Rejected Ideas)
    
    Когато се вземе решение за промяна, в края на своя отговор задължително добавяй скрит блок в точно този JSON формат:
    
    
    Ако в разговора няма нищо ново за добавяне в документацията, НЕ слагай този блок.
    """

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        temperature=0.7,
    )

    while attempts < max_retries:
        try:
            client = key_rotator.get_client()
            print(f"Извиквам Gemini с модел: {model_name} (Опит {attempts + 1})")
            
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
            error_msg = f"Грешка при връзка с Gemini с текущия ключ: {str(e)}"
            print(error_msg)
            
            # Ако имаме повече от един ключ, опитваме ротация
            if key_rotator.rotate_key():
                attempts += 1
                time.sleep(1)
                continue
            else:
                # Ако няма друг ключ или всички са преминали, хвърляме грешката
                raise Exception(error_msg)
                
        attempts += 1

    raise Exception("Всички налични Gemini API ключове изчерпиха опитите си или върнаха грешка.")

def call_gemini_api(contents_history):
    """
    Съвместим псевдоним (alias) за main_router.py, който очаква call_gemini_api.
    """
    return generate_response(contents_history)
