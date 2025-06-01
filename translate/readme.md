# Neural Machine Translation

`main.py` - English to Portuguese translator.

## Features
- Helsinki-NLP OPUS model
- Sentence splitting
- Batch processing

## Usage
```python
from translate import translate_english_to_portuguese

text = "Hello world"
translation = translate_english_to_portuguese(text)
```

## Dependencies

- transformers
