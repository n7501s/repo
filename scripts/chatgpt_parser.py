import re

def parse_chatgpt_markdown(file_content: str):
    """
    Парсира Markdown файл от ChatGPT експорт (с маркери Prompt и Response).
    Връща списък от диалогови двойки или структурирани блокове.
    """
    # Разделяме съдържанието по блокове на Prompt / Response
    # Търсим шаблони от вида "## Prompt" или подобни
    pattern = r"(##\s*Prompt.*?(?=\n##\s*Prompt|\Z))"
    raw_blocks = re.findall(pattern, file_content, re.DOTALL)
    
    parsed_conversations = []
    
    for block in raw_blocks:
        # Извличане на промпт и отговор
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

def chunk_conversation_history(parsed_data, max_chunk_size=4000):
    """
    Групира парсираните съобщения в по-малки парчета (chunks), 
    които да могат да се обработват безопасно от модела.
    """
    chunks = []
    current_chunk = ""
    
    for item in parsed_data:
        entry = f"User: {item['user']}\nAssistant: {item['assistant']}\n---\n"
        if len(current_chunk) + len(entry) > max_chunk_size:
            chunks.append(current_chunk)
            current_chunk = entry
        else:
            current_chunk += entry
            
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks
