# translate

Python module for English-to-Portuguese neural machine translation using the Helsinki-NLP OPUS-MT model (`Helsinki-NLP/opus-mt-tc-big-en-pt`). Handles sentence splitting and batching internally.

## Usage

Import as a module:

```python
from translate import translate_english_to_portuguese

text = "The company reported record earnings this quarter."
result = translate_english_to_portuguese(text)
print(result)
```

Multi-sentence input is split automatically before translation and reassembled in the output.

## Installation

```bash
uv pip install transformers torch sentencepiece
```

PyTorch installation may require a platform-specific command depending on whether you need CPU-only or CUDA support. See [pytorch.org/get-started](https://pytorch.org/get-started/locally/).

## Notes

- First run downloads model weights (~300 MB) and caches them locally.
- GPU is used automatically if available via PyTorch's device detection.
- Only English → Portuguese is supported. For other language pairs, swap the model identifier for another [Helsinki-NLP OPUS-MT](https://huggingface.co/Helsinki-NLP) checkpoint.
