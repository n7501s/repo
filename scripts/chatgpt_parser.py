import re

def parse_chatgpt_markdown(file_content: str):
    """
    Парсира Markdown файл от ChatGPT експорт (с маркери Prompt и Response).
    Връща списък от диалогови двойки или структурирани блокове.
    """
    pattern = r"(##\s*Prompt.*?(?=\n##\s*Prompt|\Z))"
    raw_blocks = re.findall(pattern, file_content, re.DOTALL)
    
    parsed_conversations = []
    
    for block in raw_blocks:
        prompt_match = re.search(r"##\s*Prompt[:\s]*(.*?)(?=\n##\s*Response|\Z)", block, re.DOTALL)
        response_match = re.search(r"##\s*Response[:\s]*(.*?)(?=\*\*Sources:\*\*|\Z)", block, re.DOTALL)
        
        prompt_text = prompt_match.group(1).strip() if prompt_match else ""
        response_text = response_match.group(1).strip() if response_match else ""
        
        if prompt_text or response_text:
            parsed_conversations.append({
                "user": prompt_text,
                "assistant": response_text
            })
            
    return parsed_conversations

def chunk_conversation_history(parsed_data, max_chunk_size=None):
    """
    Интелигентно и динамично групира парсираните съобщения в парчета (chunks).
    Ако max_chunk_size не е подаден, системата сама изчислява оптималния размер
    в зависимост от общия обем на данните, за да избегне твърде много на брой заявки.
    """
    if not parsed_data:
        return []

    # Изчисляваме общия размер на цялата история
    total_length = sum(len(item['user']) + len(item['assistant']) for item in parsed_data)
    
    # Интелигентна адаптация: ако няма зададен размер, целим се в около 15 до 25 оптимални блока
    if max_chunk_size is None:
        estimated_blocks = 20
        calculated_size = total_length // estimated_blocks
        # Задаваме граници: минимум 6000 символа, максимум 25000 символа на парче за Gemini Flash
        max_chunk_size = max(6000, min(calculated_size, 25000))
        print(f"🧠 Интелигентен анализ: Общ обем {total_length} символа. Динамично определен размер на парчето: {max_chunk_size} символа.")

    chunks = []
    current_chunk = ""
    
    for item in parsed_data:
        entry = f"User: {item['user']}\nAssistant: {item['assistant']}\n---\n"
        
        # Ако добавянето на следващия диалог надвишава динамичния лимит, затваряме текущия chunk
        if len(current_chunk) + len(entry) > max_chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = entry
        else:
            current_chunk += entry
            
    if current_chunk:
        chunks.append(current_chunk)
        
    print(f"📦 Историята е разпределена на {len(chunks)} интелигентни парчета.")
    return chunks
