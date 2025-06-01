# sentiment_analysis/

This directory contains a Python script that performs sentiment analysis on text. It uses a pre-trained Hugging Face transformer model specifically fine-tuned for sentiment analysis in Brazilian Portuguese.

## Contents:

*   `sentiment.py`: Defines a function `analisar_sentimento` that takes a string of text and returns its predicted sentiment (Positive, Negative, or Neutral) and a confidence score.

## Dependencies:

*   `transformers`: For loading and using the transformer model.
*   `torch`: The deep learning framework required by transformers.
*   `numpy`: For numerical operations.

Install the necessary libraries:
```bash
pip install transformers torch numpy
```
Note: PyTorch (`torch`) installation might require specific commands depending on your operating system and whether you want CPU or GPU support. Refer to the official PyTorch installation guide.

## Usage:

The script is designed to be imported and used as a module in other Python programs.

```python
from sentiment_analysis.sentiment import analisar_sentimento

text_to_analyze = "Este é um ótimo dia!"
sentimento, confianca = analisar_sentimento(text_to_analyze)

print(f"Text: '{text_to_analyze}'")
print(f"Sentiment: {sentimento}")
print(f"Confidence: {confianca}")
```

Running `sentiment_analysis/sentiment.py` directly will execute the example usage shown within its `if __name__ == "__main__":` block.

The model used (`lucas-leme/FinBERT-PT-BR`) was trained on financial text, so its performance on general domain text may vary, although it often provides reasonable results for standard positive/negative/neutral classification in Portuguese.
