from re import L
import pandas as pd
import json
import os
import jieba
import time
from .acv import acvMatrix , acvImage
from .lda import runLDAPipeline

def jsonable(obj):
    return isinstance(obj, (str, int, float, bool, list, dict, type(None)))
    
class ProjectManager:
    def __init__(self):
        # Project Level
        self.__project_path: str | None = None
    
        # jieba tab1 (原始數據展示層)
        self.__raw_data: list[str] = []
        self.__raw_data_attr:list[dict] = []
        self.__raw_tokenized_data: list[list[str]] = []
        self.__raw_jieba = jieba.Tokenizer(dictionary=os.path.join(os.path.dirname(__file__), "dict.txt.big"))
        
        # jieba tab2 (編輯區核心邏輯)
        self.__lock: list[bool] = []
        self.__tokenized_data: list[list[str]] = []
        self.__word_added: list[str] = []
        self.__stopwords: list[str] = []
        self.__token_schemes: dict = {}
        self.__jieba = jieba.Tokenizer(dictionary=os.path.join(os.path.dirname(__file__), "dict.txt.big"))


        # ACV tab
        self.__acv_dict: dict[str, dict] = {
            'A': {'serial':0,
                    'labels':[]}, # labels = {A/C/V}{serial}{label name}
            'C': {'serial':0,
                    'labels':[]},
            'V': {'serial':0,
                    'labels':[]}
        }
        self.__ACV_token_scheme: dict = {}
        self.__word2acvlabel: dict[str, str | None] = {}

        # LDA tab
        self.__LDA_token_scheme: dict = {}
        self.__LDA_synonyms:list[list[str] | None] = []
        self.__LDA_params:dict[str, int | float] = {
            # TODO decide params
            'n_min': 5, # for n sweeping
            'n_max': 10, # for n sweeping
            'n_final':7, # decide by user after sweeping
            'alpha': 0.1,
            'beta': 0.1,
            'iterations': 50,
            'random_state': 42,   
            'low_freq': 2,
            'high_freq': 0.4,
        }

        self.__last_lda_sweep = []
    
    def loadRawData(self, df: pd.DataFrame): 
        # Load 'text' or col 0 of csv/xlsx
        text_col = 'Comments' if 'Comments' in df.columns else df.columns[0]
        date_col = 'Dates' if 'Dates' in df.columns else df.columns[1]

        # 1. 存入主要文字列表
        self.__raw_data = df[text_col].astype(str).tolist()
        
        # 2. 存入屬性字典列表 (目前只放日期，未來可輕鬆擴充)
        self.__raw_data_attr = []
        for val in df[date_col]:
            # 強制轉換為字串存儲，避免 JSON 序列化失敗
            self.__raw_data_attr.append({
                'date': str(val) if pd.notna(val) else ""
            })


        self.__raw_tokenized_data = [list(self.__raw_jieba.cut(s)) for s in self.__raw_data]

        self.__lock = [False] * len(self.__raw_data)
        self.__word_added = []
        self.__stopwords = []
        self.__jieba = jieba.Tokenizer(dictionary=os.path.join(os.path.dirname(__file__), "dict.txt.big"))
        
    # OK
    def addMergeWord(self, IDs:dict[int,list[int]]) -> str | None:
        """將選定的 tokens 合併為新詞，並加入分詞器"""
        if len(IDs) != 1:
            return "⚠️您不可以合併不連續的詞彙!"
            
        setenceID  = list(IDs.keys())[0]
        assert 0 <= setenceID < len(self.__raw_data), f'Setence Id out of range'
        tokenIDs = IDs[setenceID]
            
        # check if tokenIDs are in range
        assert all(0 <= i < len(self.__tokenized_data[setenceID]) for i in tokenIDs), f'Token Id out of range'
        
 
        sorted_tokenIDs = sorted(tokenIDs)
        if len(sorted_tokenIDs) <=1:
            return

        for i in range(len(sorted_tokenIDs) - 1):
            if sorted_tokenIDs[i+1] != sorted_tokenIDs[i] + 1:
                return "⚠️您不可以合併不連續的詞彙!"

        _tokens = self.__tokenized_data[setenceID]
        new_word = "".join(_tokens[sorted_tokenIDs[0]:sorted_tokenIDs[-1]+1])
        _tokens = _tokens[:sorted_tokenIDs[0]] + [new_word] + _tokens[sorted_tokenIDs[-1]+1:]
        self.__tokenized_data[setenceID] = _tokens
        
        # Merge That word and lcut other unlocked sentences 
        self.lockSentence(setenceID)
        if new_word and new_word not in self.__word_added:
            self.__jieba.add_word(new_word)
            self.__word_added.append(new_word)

        for idx in range(len(self.__raw_data)):
            if not self.__lock[idx]:
                self.__tokenized_data[idx] = list(self.__jieba.cut(str(self.__raw_data[idx])))

        self.lockSentence(setenceID)

    # OK
    def splitWords(self, IDs:dict[int,list[int]]) -> str | None:
        """將選定的 tokens 分割為新詞，並加入分詞器"""
        for setenceID in IDs:
            assert 0 <= setenceID < len(self.__raw_data), f'Setence Id out of range'
            tokenIDs = IDs[setenceID]
            
            # check if tokenIDs are in range
            assert all(0 <= i < len(self.__tokenized_data[setenceID]) for i in tokenIDs), f'Token Id out of range'

            new_setence = []
            for id, token in enumerate(self.__tokenized_data[setenceID]):
                if id in tokenIDs:
                    new_setence.extend(list(token))
                else:
                    new_setence.append(token)
            self.__tokenized_data[setenceID] = new_setence
        
    # OK
    def addStopwords(self, stopwords: str | list[str]): # for txt import or manual add
        if isinstance(stopwords, str):
            stopwords = [stopwords]

        self.__stopwords = sorted(list(set(self.__stopwords + stopwords)))

    # OK
    def removeStopwords(self, stopwords: str | list[str]): # for manual remove
        if isinstance(stopwords, str):
            stopwords = [stopwords]
            
        for word in stopwords:
            if word in self.__stopwords:
                self.__stopwords.remove(word)
    
    # OK
    def toggleStopwords(self, IDs: dict[int,list[int]]): # for editor zone 
        addlist = []
        removelist = []

        for setenceID in IDs:
            assert 0 <= setenceID < len(self.__raw_data), f'Setence Id out of range'
            tokenIDs = IDs[setenceID]

            # check if tokenIDs are in range
            assert all(0 <= i < len(self.__tokenized_data[setenceID]) for i in tokenIDs), f'Token Id out of range'
            for tokenID in tokenIDs:
                word = self.__tokenized_data[setenceID][tokenID]
                if word in self.__stopwords :
                    if word not in removelist : removelist.append(word)
                else: 
                    if word not in addlist : addlist.append(word)
        
        self.removeStopwords(removelist)
        self.addStopwords(addlist)
                         
    # OK
    def lockSentence(self, ID:int) -> str | None:
        assert 0 <= ID < len(self.__raw_data), f'Setence Id out of range'
        self.__lock[ID] = not self.__lock[ID]

    # OK
    @property
    def getProjectPath(self) -> str | None:
        return self.__project_path

    # OK
    def createProject(self, path:str) -> str | None:
        self.__project_path = path  

    # OK
    def saveProject(self) -> str | None:
        save_data = {}
        for key, value in self.__dict__.items():
            if not jsonable(value):
                continue

            clean_key = key.replace(f"_{self.__class__.__name__}__", "")
            save_data[clean_key] = value
            
        with open(self.__project_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=4)
        

    # OK
    def loadProject(self, path:str) -> str | None:
        self.__project_path = path
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for key, value in data.items():
            setattr(self, f"_{self.__class__.__name__}__{key}", value)

        self.__jieba = jieba.Tokenizer(dictionary=os.path.join(os.path.dirname(__file__), "dict.txt.big"))
        for word in self.__word_added:
            self.__jieba.add_word(word)
    
    # OK
    @property
    def raw_data(self) -> list[str]:
        return self.__raw_data

    @property
    def raw_data_attr(self) -> list[dict]:
        return self.__raw_data_attr

    @property
    def tokenized_data(self) -> list[list[str]]:
        return self.__tokenized_data
    
    @property
    def raw_tokenized_data(self) -> list[list[str]]:
        return self.__raw_tokenized_data

    @property
    def lock(self) -> list[bool]:
        return self.__lock

    @property
    def stopwords(self) -> list[str]:
        return self.__stopwords
        
    @property
    def token_schemes(self) -> dict:
        return self.__token_schemes
        
    @property
    def acv_dict(self) -> dict:
        return self.__acv_dict
        
    @property
    def word2acvlabel(self) -> dict:
        return self.__word2acvlabel
    
        
    # OK
    def saveTokenScheme(self, name:str):
        if name is None:
            return

        self.__token_schemes[name] = {
            "raw_data": self.__raw_data,
            "raw_data_attr": self.__raw_data_attr,
            "word_added": self.__word_added,
            "stopwords": self.__stopwords,
            "lock": self.__lock,
            "tokenized_data": self.__tokenized_data
        }
    # OK
    def loadTokenScheme(self,  name: str):
        assert name in self.__token_schemes, f'Token Scheme {name} not found'
        scheme = self.__token_schemes[name]
        self.__raw_data = scheme.get("raw_data", [])
        self.__raw_data_attr = scheme.get("raw_data_attr", [])
        self.__raw_tokenized_data = [list(self.__raw_jieba.cut(s)) for s in self.__raw_data]

        self.__word_added = scheme.get("word_added", [])
        self.__stopwords = scheme.get("stopwords", [])
        self.__lock = scheme.get("lock", [False] * len(self.__raw_data))
        self.__tokenized_data = scheme.get("tokenized_data", [])

        self.__jieba = jieba.Tokenizer(dictionary=os.path.join(os.path.dirname(__file__), "dict.txt.big"))
        for word in self.__word_added:
            self.__jieba.add_word(word)

    def delTokenScheme(self, name:str):
        assert name in self.__token_schemes, f'Token Scheme {name} not found'
        del self.__token_schemes[name]

    # OK
    def getNoneStopWords(self):
        count = {}
        for sentence in self.__tokenized_data:
            for token in sentence:
                if token in self.__stopwords: continue
                count[token] = count.get(token, 0) + 1
        
        sorted_count = sorted(count.items(), key=lambda x: x[1], reverse=True)
        return sorted_count

    # OK
    def addACVLabel(self, ACV:str, label:str) :
        assert ACV in ['A','C','V'], f'ACV must be A, C, or V'
        _serial = self.__acv_dict[ACV]['serial']
        new_id = f'{ACV}{_serial}-{label}'
        self.__acv_dict[ACV]['labels'].append(new_id)
        self.__acv_dict[ACV]['serial'] += 1
        return new_id

    
    # OK
    def removeACVLabel(self, label:str) : 
        ACV = label[0]
        assert ACV in ['A','C','V'], f'ACV must be A, C, or V'
        assert label in self.__acv_dict[ACV]['labels'], f'Label {label} not found in ACV labels'
        self.__acv_dict[ACV]['labels'].remove(label)
        
        for word in self.__word2acvlabel:
            if self.__word2acvlabel[word] == label:
                self.__word2acvlabel[word] = None

    # OK
    def loadTokenScheme2ACV(self, token_scheme_name:str):
        assert token_scheme_name in self.__token_schemes, f'Token Scheme {token_scheme_name} not found'
        self.__ACV_token_scheme = self.__token_schemes[token_scheme_name]

        # sort according to frequency
        count = {}
        for sentence in self.__ACV_token_scheme['tokenized_data']:
            for token in sentence:
                if token in self.__ACV_token_scheme['stopwords']: continue
                count[token] = count.get(token, 0) + 1
        
        sorted_count = sorted(count.items(), key=lambda x: x[1], reverse=True)
        self.__word2acvlabel = {token: None for token, _ in sorted_count}

    # OK
    def assignACVLabel2word(self, word:str, label:str):
        assert  word in self.__word2acvlabel, f'Word {word} not found in ACV token scheme'
        assert  label in self.__acv_dict['A']['labels'] or \
                label in self.__acv_dict['C']['labels'] or \
                label in self.__acv_dict['V']['labels'], f'Label {label} not found in ACV labels'
        self.__word2acvlabel[word] = label

    # OK
    def genACVMatrix(self) -> pd.DataFrame:
        return acvMatrix(self.__ACV_token_scheme, self.__acv_dict, self.__word2acvlabel)

    # OK
    def genACVImage(self, chosen_labels: list[list[str]], save_path: str):
        return acvImage(self.__ACV_token_scheme, self.__acv_dict, self.__word2acvlabel, chosen_labels, save_path)

    # OK
    def loadTokenScheme2LDA(self, token_scheme_name:str):
        assert token_scheme_name in self.__token_schemes, f'Token Scheme {token_scheme_name} not found'
        self.__LDA_token_scheme = self.__token_schemes[token_scheme_name]
        self.__last_lda_sweep = [] # Store last results for UI persistence

    # OK
    def loadSynonyms2LDA(self, synonyms_path: str):
        new_synonyms = []
        seen_words = set()
        with open(synonyms_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                # support both fullwidth & halfwidth = 
                parts = line.replace('＝', '=').split('=')
                syn_list = [p.strip() for p in parts if p.strip()]
                
                for word in syn_list:
                    if word in seen_words: return f'有兩行出現重複詞彙'
                    seen_words.add(word)
                new_synonyms.append(syn_list)
        
        self.__LDA_synonyms = new_synonyms

    # OK
    def removeSynonymsFromLDA(self):
        self.__LDA_synonyms = []

    # OK
    def setLDAParams(self, params:dict):
        assert params.keys() == self.__LDA_params.keys(), f'Invalid parameters'
        if params['alpha'] != 'auto' or not isinstance(params['alpha'], (int, float)):
            raise ValueError('alpha must be auto or float')
        if params['beta'] != 'auto' or not isinstance(params['beta'], (int, float)):
            raise ValueError('beta must be auto or float')
        if not isinstance(params['low_freq'], (int, float)):
            raise ValueError('low_freq must be int')
        if not isinstance(params['high_freq'], (int, float)):
            raise ValueError('high_freq must be int')
        if not isinstance(params['iterations'],  (int, float)):
            raise ValueError('iterations must be int')
        if not isinstance(params['n_min'],  (int, float)):
            raise ValueError('n_min must be int')
        if not isinstance(params['n_max'],  (int, float)):
            raise ValueError('n_max must be int')
        if not isinstance(params['n_final'],  (int, float)):
            raise ValueError('n_final must be int')
            
        self.__LDA_params = params

    # OK
    def _apply_lda_synonyms(self, tokenized_data):
        if not self.__LDA_synonyms:
            return tokenized_data
            
        syn_map = {}
        for group in self.__LDA_synonyms:
            if not group: continue
            target = group[0]
            for word in group:
                syn_map[word] = target
                
        new_data = []
        for setence in tokenized_data:
            new_data.append([syn_map.get(w, w) for w in setence])
        return new_data

    def _filter_stopwords(self, tokenized_data, stopwords):
        new_data = []
        for sentence in tokenized_data:
            new_sentence = [word for word in sentence if word not in stopwords]
            new_data.append(new_sentence)
        return new_data

    def genLDASweep(self, params_dict: dict, save_dir: str, prefix: str):
        tokenized_data = self.__LDA_token_scheme.get('tokenized_data', [])
        if not tokenized_data:
            raise ValueError("請先載入分詞方案以進行 LDA 分析。")

        tokenized_data = self._filter_stopwords(tokenized_data, self.__LDA_token_scheme.get('stopwords', []))
        tokenized_data = self._apply_lda_synonyms(tokenized_data)
        
        n_min = int(params_dict['n_min'])
        n_max = int(params_dict['n_max'])
        
        results = []
        for k in range(n_min, n_max + 1):
            perpl, coh, _, _, _ = runLDAPipeline(
                tokenized_docs=tokenized_data,
                num_topics = k, 
                alpha = params_dict['alpha'], beta = params_dict['beta'],
                use_tfidf = params_dict.get('use_tfidf', True), 
                no_below = params_dict['low_freq'], no_above = params_dict['high_freq'], 
                iterations = params_dict['iterations'],
                random_state = params_dict.get('random_state', 42),
                save_prefix = os.path.join(save_dir, prefix),
                run_viz = False
            )
            results.append({"k": k, "perplexity": perpl, "coherence": coh})
        self.__last_lda_sweep = results
        return results
    
    @property
    def last_lda_sweep(self):
        return self.__last_lda_sweep

    def genLDAFinal(self, params_dict: dict, save_dir: str, prefix: str):
        tokenized_data = self.__LDA_token_scheme.get('tokenized_data', [])
        if not tokenized_data:
            raise ValueError("請先載入分詞方案以進行 LDA 分析。")
        
        tokenized_data = self._filter_stopwords(tokenized_data, self.__LDA_token_scheme.get('stopwords', []))
        tokenized_data = self._apply_lda_synonyms(tokenized_data)
        

        perpl, coh, vis_data, df_word_dist, df_doc_topics = runLDAPipeline(
                tokenized_docs=tokenized_data,
                num_topics = params_dict['n_final'], 
                alpha = params_dict['alpha'], beta = params_dict['beta'],
                use_tfidf = params_dict.get('use_tfidf', True), 
                no_below = params_dict['low_freq'], no_above = params_dict['high_freq'], 
                iterations = params_dict['iterations'],
                random_state = params_dict.get('random_state', 42),
                save_prefix = os.path.join(save_dir, prefix),
                run_viz = True,
                doc_dates = [attr.get('date', '') for attr in self.__raw_data_attr]
            )

        return {
            "k": params_dict['n_final'], 
            "perplexity": perpl, 
            "coherence": coh,
            "vis_data": vis_data,
            "df_word_dist": df_word_dist,
            "df_doc_topics": df_doc_topics
        }
    
