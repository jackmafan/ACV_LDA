# ACV-LDA

本系統是一套整合了「中文分詞編輯」、「ACV 手段目的鏈分析」與「LDA 主題建模」的桌面端工具。請遵循以下導航流程以完成完整的分析任務。

---

# 安裝

請確認是否有安裝 conda 虛擬環境，在想安裝的資料夾中開啟 PowerShell 後，輸入以下指令

```bash
conda create -n ACV_LDA python=3.12 -y
conda activate ACV_LDA
conda install git
git clone https://github.com/jackmafan/ACV_LDA.git
cd ACV_LDA 
pip install -r requirements.txt
pyinstaller --noconfirm --onefile --windowed --add-data "src/core/dict.txt.big;src/core" src/main.py
```

如欲直接以python啟動
```bash
conda activate ACV_LDA
cd ACV_LDA
python src/main.py
```
如欲編譯成執行檔
```bash
conda activate ACV_LDA
cd ACV_LDA
pyinstaller main.spec
```
即可在ACV_LDA/dist資料夾下即可找到編譯完後的執行檔


# 使用

## 專案準備與數據載入

* **建立專案**：啟動後請先點擊「建立新專案」以初始化工作目錄。

## 建立分詞表

### a.載入初步結果

* **數據匯入**：匯入 Excel 檔案時，系統會自動辨識：
  * `Comments` (或首欄)：作為主要分析文本。
  * `Dates` (或次欄)：作為日期序列（用於 LDA 熱圖分析）。
  * 註：若無日期欄位，LDA 系統無法產生時間對主題的 Heatmap。

### b.編輯與停用詞設定

* 點擊字詞即可選取詞彙，點擊左上方的**取消選取[ESC]**按鈕即可取消選取所有的字詞
* **合併詞彙[M]**：若選取的詞彙連續，執行合併後，系統會自動合併目標詞並**重新斷開**其他非鎖定句子（不再需要強制合併按鈕）。NOTE: 同句其他處仍須手動編輯
* **停用詞[S]**：可以將選取的多個詞會設為/取消設為停用詞，在停用詞列表中，**多點擊一下**已選詞彙即可將其從「加入」狀態切換為「移除」，操作更直覺。
* **拆分詞彙[D]**：拆詞可將一個詞分成一個一個字以方便重新組合。拆分功能現在支援 **「批量操作」**，可對多個選定詞彙同時執行。
* **方案儲存**：當前斷詞結果會隨專案存檔，但若要進行 ACV 或 LDA 分析，必須在 **2.編輯與停用詞設定** 字面板中**輸入方案名稱並按下「儲存方案」**。

### c. 關鍵詞頻結果

* 提供斷詞詞頻成果預覽，也可以預覽在哪些句子中出現過這些詞彙。
* 您可以在這邊輸出結果txt，接著回到 **2.編輯與停用詞設定** 批量匯入停用詞。

## 2. ACV 分析

* **標註流程**：
    1. 建立標籤類別 (A/C/V)。
    2. 載入已儲存的「分詞方案」。
    3. 為感興趣的詞彙標註分類。
* **產出結果**：
  * 預覽並輸出 **「蘊含矩陣 (Implication Matrix)」**。
  * 產出 **「簡易向量圖 (HVM 图)」**。

## 🧬 3. LDA 主題建模分析 (LDA Tab)

* 在進行分析前，一樣要先選擇一個斷詞方案。
* 載入同義詞：您可以載入一個每行指定一組如`字詞1=字詞2=字詞3`形式的txt, 系統會將這些詞視作相同的詞進行分析
* 參數設置
  * alpha: 不建議更動，預設 auto (模型自動設定)
  * beta: 不建議更動，預設 auto (模型自動設定)
  * iteration: LDA 建立模型時的迭代次數，
  * n_min: 低頻過濾，低於此**次數** 的詞彙被排除
  * n_max: 高頻過濾，出現在高於此**比例**句子的詞彙會被排除
  * 使用TF-IDF過濾模式: 推薦開啟，可以降低在很多句子中都常見的詞彙。
* **分析策略**：推薦先使用 **「Sweep (參數尋優)」** 功能。會從 sweep 下限到 sweep 上限，分析每個主題數的 **困惑度 (Perplexity)** 與 **一致性 (Coherence)**
* **尋優指標**：觀察 **困惑度 (Perplexity)** 與 **一致性 (Coherence)** 的交叉點，決定最佳主題數填入**Final主題數**。
* **Final 分析輸出**：決定 K 值後執行 Final 分析，系統將自動產出：
    1. **pyLDAvis** (.html)：主題分佈互動網頁，視覺化主題間的距離與詞彙權重。
    2. **桑基圖** (.html)：主題-詞彙權重流向圖，呈現主題演變為關鍵詞的過程。
    3. **時間演化熱圖** (.png)：主題隨時間（十等分區間）的機率起伏趨勢。
    4. **word_distribution.csv**：列出各個主題的前 20 名核心關鍵字及其權重，是定義標籤主題意義的主要依據。
    5. **topics.csv**：記錄每一條原始評論在各個主題上的分佈機率，可用於後續的統計回歸或進階標籤分類。

---

## 🔗 相關資源

* [Gensim LDA 官方教學](https://radimrehurek.com/gensim/auto_examples/tutorials/run_lda.html)
