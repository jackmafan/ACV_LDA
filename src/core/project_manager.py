from re import L
from curses import OK
import pandas as pd
import json
import os
import jieba
import time

def jsonable(obj):
    return isinstance(obj, (str, int, float, bool, list, dict, type(None)))
    
class ProjectManager:
    def __init__(self):
        # Project Level
        self.__project_path: str | None = None
    
        # jieba tab1 (原始數據展示層)
        self.__raw_data: list[str] = []
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

    
    # OK
    def loadRawData(self, df: pd.DataFrame): 
        # Load 'text' or col 0 of csv/xlsx
        text_col = 'Comments' if 'Comments' in df.columns else df.columns[0]

        # Set raw data
        self.__raw_data = df[text_col].astype(str).tolist()
        print("start") 
        _start = time.time()
        self.__raw_tokenized_data = [list(self.__raw_jieba.cut(s)) for s in self.__raw_data]
        print("end", time.time() - _start)
        # 
        self.__tokenized_data = [list(tokens) for tokens in self.__raw_tokenized_data]
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
        if not self.__ACV_token_scheme or 'tokenized_data' not in self.__ACV_token_scheme:
            return pd.DataFrame()

        a_lbls = self.__acv_dict['A']['labels']
        c_lbls = self.__acv_dict['C']['labels']
        v_lbls = self.__acv_dict['V']['labels']
        
        row_headers = a_lbls + c_lbls
        col_headers = c_lbls + v_lbls
        
        matrix = pd.DataFrame(0.0, index=row_headers, columns=col_headers)
        
        for tokens in self.__ACV_token_scheme['tokenized_data']:
            if not tokens: continue
            
            # Map tokens to their labels
            sentence_labels = []
            for word in tokens:
                label = self.__word2acvlabel.get(word)
                if label:
                    sentence_labels.append(label)
                    
            if len(sentence_labels) <= 1:
                continue
                
            for i in range(len(sentence_labels)):
                for j in range(i + 1, len(sentence_labels)):
                    l1 = sentence_labels[i]
                    l2 = sentence_labels[j]
                    
                    if l1 == l2: continue
                    
                    cat1 = l1[0]
                    cat2 = l2[0]
                    
                    row_key = None
                    col_key = None
                    
                    score = 1.0 if j == i + 1 else 0.01
                    
                    if cat1 == 'A':
                        row_key = l1
                        if cat2 in ['C', 'V']: col_key = l2
                    elif cat1 == 'C':
                        if cat2 == 'A':
                            row_key = l2
                            col_key = l1
                        elif cat2 == 'C':
                            row_key = l1
                            col_key = l2
                        elif cat2 == 'V':
                            row_key = l1
                            col_key = l2
                    elif cat1 == 'V':
                        col_key = l1
                        if cat2 in ['A', 'C']: row_key = l2

                    if row_key and col_key and row_key in matrix.index and col_key in matrix.columns:
                        matrix.at[row_key, col_key] += score

        return matrix
    