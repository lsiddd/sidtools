# Passo 1: Instalar as bibliotecas necessárias
# pip install transformers torch numpy

from transformers import AutoTokenizer, BertForSequenceClassification
import torch
import numpy as np

# Passo 2: Carregar o modelo pré-treinado para análise de sentimentos em português
model_name = "lucas-leme/FinBERT-PT-BR"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = BertForSequenceClassification.from_pretrained(model_name)

# Mapeamento dos rótulos
label_mapper = {
    0: "POSITIVO",
    1: "NEGATIVO",
    2: "NEUTRO"
}

# Passo 3: Função de análise de sentimentos
def analisar_sentimento(texto):
    # Tokenização
    inputs = tokenizer(
        texto,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=512
    )
    
    # Passar pelo modelo
    with torch.no_grad():
        outputs = model(**inputs)

    # Obter probabilidades
    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
    probs = probs.numpy()[0]
    
    # Determinar o rótulo com maior probabilidade
    sentimento = label_mapper[np.argmax(probs)]
    confianca = round(np.max(probs), 3)
    
    return sentimento, confianca

# Exemplo de uso
texto_positivo = "Adorei este produto! Funciona perfeitamente e a entrega foi rápida."
texto_negativo = "Péssima experiência. O serviço foi horrível e o produto quebrou no primeiro dia."

# print(analisar_sentimento(texto_positivo))  # Exemplo: ('POSITIVO', 0.876)
# print(analisar_sentimento(texto_negativo))  # Exemplo: ('NEGATIVO', 0.652)
print(analisar_sentimento("o almoço vai ser ótimo"))  # Exemplo: ('NEGATIVO', 0.652)
