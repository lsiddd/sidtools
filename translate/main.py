from transformers import MarianMTModel, MarianTokenizer

def translate_english_to_portuguese(text: str, max_length: int = 512) -> str:
    """
    Translate English text to Portuguese using a local neural machine translation model
    """
    # Load pre-trained model and tokenizer
    model_name = "Helsinki-NLP/opus-mt-tc-big-en-pt"
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)

    # Split text into sentences if needed (better for long texts)
    sentences = [text]  # For simplicity, you can add sentence splitting here
    
    translated = []
    
    for sentence in sentences:
        # Tokenize input
        inputs = tokenizer(sentence, return_tensors="pt", max_length=max_length, truncation=True)
        
        # Translate
        outputs = model.generate(**inputs)
        
        # Decode output
        translated_sentence = tokenizer.decode(outputs[0], skip_special_tokens=True)
        translated.append(translated_sentence)
    
    return " ".join(translated)

# Example usage
if __name__ == "__main__":
    english_text = "Hello, how are you? This is a translation test using a local model."
    translation = translate_english_to_portuguese(english_text)
    print("English:", english_text)
    print("Portuguese:", translation)
