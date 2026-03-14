import jieba
import pandas as pd
import os
from typing import List, Dict, Set, Tuple

class Tokenizer:
    def __init__(self):
        # We will keep a local instance of jieba configuration if needed, 
        # but for simplicity, we use the global jieba module first.
        
        # Automatically load the custom large dictionary if it exists
        dict_path = os.path.join(os.path.dirname(__file__), "dict.txt.big")
        if os.path.exists(dict_path):
            jieba.set_dictionary(dict_path)
            
        self.user_dict = set() # Words explicitly added by the user
        self.stop_words = set() # Words explicitly removed by the user

    def to_dict(self) -> Dict:
        return {
            "user_dict": list(self.user_dict),
            "stop_words": list(self.stop_words)
        }

    def from_dict(self, data: Dict):
        self.user_dict = set()
        self.stop_words = set()
        if "user_dict" in data:
            self.load_user_dict(data["user_dict"])
        if "stop_words" in data and isinstance(data["stop_words"], list):
            for w in data["stop_words"]:
                if w:
                    self.add_stop_word(str(w))
        
        print(f"[Tokenizer] Loaded {len(self.user_dict)} custom words and {len(self.stop_words)} stop words.")

    def load_user_dict(self, words: List[str]):
        """Load a list of custom words into jieba."""
        for w in words:
            self.add_word(w)

    def add_word(self, word: str):
        """Add a custom word to jieba and our tracking set."""
        self.user_dict.add(word)
        jieba.add_word(word)
        # If it was a stop word, un-stop it
        if word in self.stop_words:
            self.stop_words.remove(word)

    def remove_word(self, word: str):
        """Remove a custom word from jieba's dictionary."""
        jieba.del_word(word)
        if word in self.user_dict:
            self.user_dict.remove(word)

    def add_stop_word(self, word: str):
        self.stop_words.add(word)

    def remove_stop_word(self, word: str):
        if word in self.stop_words:
            self.stop_words.remove(word)

    def load_stop_words(self, words: List[str]):
        for w in words:
            self.stop_words.add(w)

    def tokenize(self, text: str) -> List[str]:
        """Tokenize a single text string."""
        if pd.isna(text) or not isinstance(text, str):
            return []
        tokens = list(jieba.cut(text))
        # Filter out whitespace, but KEEP stop words here so the UI can render them
        return [t for t in tokens if t.strip()]

    def tokenize_series(self, series: pd.Series) -> pd.Series:
        """Tokenize a pandas Series of text."""
        return series.apply(self.tokenize)

    def get_word_counts(self, tokenized_docs: pd.Series) -> pd.Series:
        """Count frequencies of all words across all documents."""
        all_words = []
        for doc_tokens in tokenized_docs:
            valid_words = [t for t in doc_tokens if t not in self.stop_words]
            all_words.extend(valid_words)
        return pd.Series(all_words).value_counts()
