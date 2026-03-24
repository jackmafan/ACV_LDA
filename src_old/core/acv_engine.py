import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

class ACVEngine:
    def __init__(self, category_dict: Dict[str, str]):
        self.category_dict = category_dict  # Mapping: Word -> 'A', 'C', OR 'V'

    def filter_tokens_by_dictionary(self, tokenized_series: pd.Series) -> pd.Series:
        """Keep only tokens that are defined in the category dictionary."""
        def filter_doc(tokens):
            return [t for t in tokens if t in self.category_dict]
        return tokenized_series.apply(filter_doc)

    def calculate_cooccurrence(self, tokenized_series: pd.Series) -> pd.DataFrame:
        """Calculate word co-occurrence matrix at the document level."""
        # Note: A word co-occurs with another if they both appear in the same document.
        # This implementation simply counts documents where both words appeared.
        word_list = list(self.category_dict.keys())
        word_idx = {w: i for i, w in enumerate(word_list)}
        n_words = len(word_list)
        
        co_mat = np.zeros((n_words, n_words), dtype=int)
        
        # We uniquely count words per document for co-occurrence (standard bag of words approach)
        for tokens in tokenized_series:
            unique_tokens = set([t for t in tokens if t in self.category_dict])
            token_indices = [word_idx[t] for t in unique_tokens]
            
            # Increment co-occurrence for all pairs in the document
            for i in token_indices:
                for j in token_indices:
                    co_mat[i, j] += 1
                    
        return pd.DataFrame(co_mat, index=word_list, columns=word_list)

    def generate_transition_matrices(self, co_mat: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Calculate P(C|A) and P(V|C) Matrices.
        P(B|A) = count(A & B) / count(A)
        """
        words = list(co_mat.index)
        
        A_words = [w for w in words if self.category_dict.get(w) == 'A']
        C_words = [w for w in words if self.category_dict.get(w) == 'C']
        V_words = [w for w in words if self.category_dict.get(w) == 'V']
        
        # 1. P(C|A) = count(A & C) / count(A)
        # count(A) is found on the diagonal of co-occurrence: co_mat.loc[A, A]
        P_C_given_A = pd.DataFrame(0.0, index=A_words, columns=C_words)
        for a in A_words:
            count_A = co_mat.loc[a, a]
            if count_A > 0:
                for c in C_words:
                    count_AC = co_mat.loc[a, c]
                    P_C_given_A.loc[a, c] = count_AC / count_A
                    
        # 2. P(V|C) = count(C & V) / count(C)
        P_V_given_C = pd.DataFrame(0.0, index=C_words, columns=V_words)
        for c in C_words:
            count_C = co_mat.loc[c, c]
            if count_C > 0:
                for v in V_words:
                    count_CV = co_mat.loc[c, v]
                    P_V_given_C.loc[c, v] = count_CV / count_C
                    
        return P_C_given_A, P_V_given_C

    def generate_sankey_data(self, P_C_given_A: pd.DataFrame, P_V_given_C: pd.DataFrame, threshold=0.0):
        """
        Format the transition matrices into Source-Target-Value links for Sankey plotting.
        """
        links = []
        
        # A to C
        for a_word in P_C_given_A.index:
            for c_word in P_C_given_A.columns:
                val = P_C_given_A.loc[a_word, c_word]
                if val > threshold:
                    links.append({
                        'source': a_word,
                        'target': c_word,
                        'value': val
                    })
                    
        # C to V
        for c_word in P_V_given_C.index:
            for v_word in P_V_given_C.columns:
                val = P_V_given_C.loc[c_word, v_word]
                if val > threshold:
                    links.append({
                        'source': c_word,
                        'target': v_word,
                        'value': val
                    })
                    
        return links
