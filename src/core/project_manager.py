import pandas as pd
from typing import List, Dict, Optional
import json
import os
from .tokenizer import Tokenizer

class ProjectManager:
    def __init__(self):
        self.raw_data: Optional[pd.DataFrame] = None
        self.text_column: str = ''
        self.tokenizer = Tokenizer()
        
        # State
        self.tokenized_data: Optional[pd.Series] = None
        self.word_counts: Optional[pd.Series] = None
        
        # Original state for diffing and baseline UI
        self.original_word_counts: Optional[pd.Series] = None
        self.original_tokenized_data: Optional[pd.Series] = None
        
        # Category Dictionary mapping Word -> Type ('A', 'C', 'V')
        self.category_dict: Dict[str, str] = {}
        
        # Sentences manually locked by the user: mapping of active indices to ignore during _retokenize
        self.locked_sentences = set()

        # ACV Dictionaries
        self.acv_dict: Dict[str, List[str]] = {
            'A': [],
            'C': [],
            'V': []
        }
        self.schemes: Dict[str, Dict] = {}
        self.acv_schemes: Dict[str, Dict] = {}
        
    def get_acv_words(self, category_type: str) -> List[str]:
        """Get the list of words for an A, C, or V category."""
        return self.acv_dict.get(category_type, [])
        
    def add_acv_word(self, category_type: str, word: str):
        """Add a word to an ACV category list."""
        if category_type in self.acv_dict and word not in self.acv_dict[category_type]:
            self.acv_dict[category_type].append(word)
            
    def remove_acv_word(self, category_type: str, word: str):
        """Remove a word from an ACV category list."""
        if category_type in self.acv_dict and word in self.acv_dict[category_type]:
            self.acv_dict[category_type].remove(word)

    def load_raw_data(self, df: pd.DataFrame, text_column: str):
        """Load raw pandas dataframe and specify which column contains the text."""
        self.raw_data = df.copy()
        if text_column not in self.raw_data.columns:
            raise ValueError(f"Column '{text_column}' not found in data.")
        self.text_column = text_column
        
        # Initial tokenization
        self._retokenize(is_initial=True)

    def _retokenize(self, is_initial=False):
        """Re-run tokenization on the raw text."""
        if self.raw_data is None or not self.text_column:
            return
            
        new_tokenized_data = self.tokenizer.tokenize_series(self.raw_data[self.text_column])
        
        if getattr(self, 'tokenized_data', None) is not None and getattr(self, 'locked_sentences', None):
            for i in self.locked_sentences:
                if i < len(self.tokenized_data) and i < len(new_tokenized_data):
                    new_tokenized_data.iloc[i] = self.tokenized_data.iloc[i]
                    
        self.tokenized_data = new_tokenized_data
        self._update_word_counts()
        
        if is_initial:
            self.original_word_counts = self.word_counts.copy()
            self.original_tokenized_data = self.tokenized_data.copy()

    def toggle_lock(self, sentence_idx: int):
        """Toggle the lock state of a sentence."""
        if not hasattr(self, 'locked_sentences'):
            self.locked_sentences = set()
            
        if sentence_idx in self.locked_sentences:
            self.locked_sentences.remove(sentence_idx)
        else:
            self.locked_sentences.add(sentence_idx)

    def split_token(self, sentence_idx: int, token_idx: int):
        """Locally split a word into individual characters in a sentence without locking it."""
        if self.tokenized_data is None:
            return
        tokens = list(self.tokenized_data.iloc[sentence_idx])
        if token_idx < len(tokens):
            word = tokens[token_idx]
            if len(word) > 1:
                new_tokens = tokens[:token_idx] + list(word) + tokens[token_idx+1:]
                self.tokenized_data.iloc[sentence_idx] = new_tokens
                self._update_word_counts()
                
    def force_local_merge(self, sentence_idx: int, indices: List[int], merged_word: str):
        """Force merge tokens locally without updating the global dictionary or retokenizing."""
        if self.tokenized_data is None:
            return
        tokens = list(self.tokenized_data.iloc[sentence_idx])
        start_idx = min(indices)
        end_idx = max(indices)
        new_tokens = tokens[:start_idx] + [merged_word] + tokens[end_idx+1:]
        self.tokenized_data.iloc[sentence_idx] = new_tokens
        self._update_word_counts()

    def _update_word_counts(self):
        """Update word counts based on the current tokenized_data."""
        if self.tokenized_data is not None:
            self.word_counts = self.tokenizer.get_word_counts(self.tokenized_data)
        else:
            self.word_counts = None
                
    def merge_tokens_local_and_global(self, sentence_idx: int, indices: List[int], merged_word: str):
        """Merge tokens locally if locked, and add standard global entry."""
        if sentence_idx in self.locked_sentences:
            tokens = list(self.tokenized_data.iloc[sentence_idx])
            start_idx = min(indices)
            end_idx = max(indices)
            new_tokens = tokens[:start_idx] + [merged_word] + tokens[end_idx+1:]
            self.tokenized_data.iloc[sentence_idx] = new_tokens
            
        self.tokenizer.add_word(merged_word)
        self._retokenize()

    def add_custom_word(self, word: str):
        """Add a custom word and retokenize."""
        self.tokenizer.add_word(word)
        self._retokenize()

    def remove_custom_word(self, word: str):
        """Remove a custom word and retokenize."""
        self.tokenizer.remove_word(word)
        self._retokenize()

    def add_stop_word(self, word: str):
        """Mark a word as a stop word and update statistics."""
        self.tokenizer.add_stop_word(word)
        self._update_word_counts()
        
    def remove_stop_word(self, word: str):
        """Remove a word from stop words and update statistics."""
        self.tokenizer.remove_stop_word(word)
        self._update_word_counts()

    def load_stop_words_from_file(self, filepath: str):
        """Load stop words from a text file (one word per line) and update statistics."""
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        words = [line.strip() for line in lines if line.strip()]
        self.tokenizer.load_stop_words(words)
        self._update_word_counts()
        
    def get_word_diff(self) -> pd.DataFrame:
        """Compare current word counts with the original word counts."""
        if self.original_word_counts is None or self.word_counts is None:
            return pd.DataFrame()
            
        orig = self.original_word_counts.rename('Original Count')
        curr = self.word_counts.rename('Current Count')
        
        diff_df = pd.concat([orig, curr], axis=1).fillna(0)
        diff_df['Difference'] = diff_df['Current Count'] - diff_df['Original Count']
        
        # Return only words that have changed
        return diff_df[diff_df['Difference'] != 0].sort_values('Difference', ascending=False)

    def load_category_dictionary(self, category_df: pd.DataFrame, word_col: str, cat_col: str):
        """Load A-C-V mapping from a DataFrame."""
        self.category_dict = {}
        for _, row in category_df.iterrows():
            word = str(row[word_col]).strip()
            cat = str(row[cat_col]).strip().upper()
            if cat in ['A', 'C', 'V']:
                self.category_dict[word] = cat
                
    def get_valid_keywords(self) -> pd.Series:
        """Returns the word counts excluding stop words."""
        if self.tokenized_data is None:
            return pd.Series()
        
        all_words = []
        for tokens in self.tokenized_data:
            valid_words = [t for t in tokens if t not in self.tokenizer.stop_words]
            all_words.extend(valid_words)
        return pd.Series(all_words).value_counts()
        
    def save_scheme(self, name: str):
        """Save the current tokenization state as a named scheme."""
        if not hasattr(self, 'schemes'):
            self.schemes = {}
            
        self.schemes[name] = {
            "locked_sentences": list(self.locked_sentences) if hasattr(self, 'locked_sentences') else [],
            "edited_tokenized_data": [list(x) for x in self.tokenized_data] if self.tokenized_data is not None else None,
            "tokenizer": self.tokenizer.to_dict() # This includes stop_words and user_dict
        }
        
    def delete_scheme(self, name: str):
        """Delete a saved scheme by name."""
        if hasattr(self, 'schemes') and name in self.schemes:
            del self.schemes[name]
            
    def load_scheme(self, name: str):
        """Load a saved tokenization scheme and replace current state."""
        if not hasattr(self, 'schemes') or name not in self.schemes:
            raise ValueError(f"找不到名為 '{name}' 的斷詞方案。")
            
        scheme = self.schemes[name]
        
        # Restore Locks
        self.locked_sentences = set(scheme.get("locked_sentences", []))
        
        # Restore edited tokenized data
        edited_data = scheme.get("edited_tokenized_data")
        if edited_data is not None:
            # Need to convert list of lists back to a Pandas Series containing lists
            self.tokenized_data = pd.Series(edited_data)
        else:
            self.tokenized_data = None
            
        # Restore tokenizer (stop words, custom weights)
        tokenizer_data = scheme.get("tokenizer")
        if tokenizer_data:
            # from_dict already clears and reloads user_dict and stop_words
            self.tokenizer.from_dict(tokenizer_data)
            
        # Update word counts based on the restored tokenized_data and tokenizer
        self._update_word_counts()
                
    def get_project_state(self) -> Dict:
        """Return a summary of the current project state."""
        return {
            'has_data': self.raw_data is not None,
            'num_documents': len(self.raw_data) if self.raw_data is not None else 0,
            'num_unique_words': len(self.word_counts) if self.word_counts is not None else 0,
            'num_category_words': len(self.category_dict),
            'custom_dictionary_size': len(self.tokenizer.user_dict)
        }

    def save_project(self, filepath: str):
        """Save the project state to a .aproj JSON file."""
        if not filepath.endswith('.aproj'):
            filepath += '.aproj'
            
        state = {
            "text_column": self.text_column,
            "category_dict": self.category_dict,
            "tokenizer": self.tokenizer.to_dict(),
            "locked_sentences": list(self.locked_sentences) if hasattr(self, 'locked_sentences') else [],
            "edited_tokenized_data": [list(x) for x in self.tokenized_data] if self.tokenized_data is not None else None,
            "schemes": getattr(self, 'schemes', {}),
            "acv_dict": self.acv_dict,
            "acv_schemes": self.acv_schemes
        }
        
        # Save raw data as a list of dictionaries if it exists
        if self.raw_data is not None:
            # We only strictly need the text column for the core, but saving all columns is safer
            state["raw_data_records"] = self.raw_data.to_dict(orient="records")
        else:
            state["raw_data_records"] = None
            
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def load_project(self, filepath: str):
        """Load the project state from a .aproj JSON file."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Project file not found: {filepath}")
            
        with open(filepath, 'r', encoding='utf-8') as f:
            state = json.load(f)
            
        self.text_column = state.get("text_column", "")
        self.category_dict = state.get("category_dict", {})
        self.schemes = state.get("schemes", {})
        self.acv_schemes = state.get("acv_schemes", {})
        self.acv_dict = state.get("acv_dict", {'A': [], 'C': [], 'V': []})
        
        # Restore raw data and retokenize
        records = state.get("raw_data_records")
        if records:
            self.raw_data = pd.DataFrame(records)
            
            # 1. Store the loaded tokenizer state temporarily
            loaded_tokenizer_state = state.get("tokenizer", {})
            
            # Support both new array and legacy tuple lock storage
            self.locked_sentences = set(state.get("locked_sentences", []))
            legacy_locked_data = state.get("locked_sentences_data", {})
            edited_tokens = state.get("edited_tokenized_data", None)
            
            # 2. Clear current tokenizer to get the raw pure baseline
            self.tokenizer = Tokenizer()
            self._retokenize(is_initial=True)
            
            # 3. Apply the loaded user configuration
            self.tokenizer.from_dict(loaded_tokenizer_state)
            
            # 4. Restore data
            if edited_tokens is not None:
                # Modern format: explicitly restore all tokens exactly as they were
                self.tokenized_data = pd.Series(edited_tokens)
                self._update_word_counts()
            else:
                # Legacy fallback format
                if self.tokenized_data is not None:
                    for k, v in legacy_locked_data.items():
                        idx = int(k)
                        self.locked_sentences.add(idx)
                        if idx < len(self.tokenized_data):
                            self.tokenized_data.iloc[idx] = v
                self._retokenize(is_initial=False)
        else:
            self.raw_data = None
            self.tokenized_data = None
            self.original_tokenized_data = None
            self.word_counts = None
            self.original_word_counts = None
