import os
import math
import pandas as pd
from gensim.corpora import Dictionary
from gensim.models import LdaModel, TfidfModel, CoherenceModel
import pyLDAvis
import pyLDAvis.gensim_models as gensimvis

from pyecharts import options as opts
from pyecharts.charts import Sankey,Graph

import seaborn as sns
import matplotlib.pyplot as plt


def len2passes(num_sentences):
    if num_sentences < 1000:
        return 30
    elif num_sentences < 10000:
        return 20
    elif num_sentences < 10_0000:
        return 10
    elif num_sentences < 1000_0000:
        return 5
    else:
        return 1

def runLDAPipeline(tokenized_docs, num_topics, alpha, beta, use_tfidf, no_below, no_above, iterations, random_state, save_prefix, run_viz=True, doc_dates=None):
    """
    Run a single LDA pipeline and output requested files.
    Returns: perplexity, coherence, vis_data, df_word_dist, df_doc_topics
    """
    __BEGINMSG = f"""
    Running LDA with {num_topics} topics, {iterations} iterations, {alpha} alpha, {beta} beta, {use_tfidf} use_tfidf, {no_below} no_below, {no_above} no_above, {random_state} random_state, {save_prefix} save_prefix
    """
    print(__BEGINMSG)
    if not tokenized_docs:
        raise ValueError("沒有足夠的文本來進行 LDA 分析。")

    # 1. 建立字典與過濾
    dictionary = Dictionary(tokenized_docs) # Build token <-> id 
    n_b = float(no_below) if '.' in str(no_below) else int(no_below) # drop words lower than 'n_b' counts
    n_a = float(no_above) # drop words shows in more than 100*n_a% sentences
    dictionary.filter_extremes(no_below=n_b, no_above=n_a)
    
    print(f"Dictionary after filter has {len(dictionary)} tokens.")
    
    # 2. 建立語料庫
    corpus = [dictionary.doc2bow(doc) for doc in tokenized_docs]
    if not corpus or len(dictionary) == 0:
        raise ValueError("字典在過濾後為空，請放寬高低頻過濾參數。")
        
    # 3. TF-IDF
    if use_tfidf:
        tfidf = TfidfModel(corpus)
        corpus_for_lda = tfidf[corpus]
    else:
        corpus_for_lda = corpus
        
    # 4. 訓練 LDA
    a_param = alpha if alpha == 'auto' else 'symmetric'
    try:
        a_param = float(alpha)
    except:
        pass
        
    b_param = beta if beta == 'auto' else 'symmetric'
    try:
        b_param = float(beta)
    except:
        pass

    lda_model = LdaModel(
        corpus=corpus_for_lda,
        id2word=dictionary,
        num_topics=num_topics,
        random_state=random_state,
        iterations=int(iterations),
        passes=len2passes(len(tokenized_docs)),
        alpha=a_param,
        eta=b_param
    )
    
    # 5. 計算指標
    log_perpl = lda_model.log_perplexity(corpus_for_lda)
    perplexity = math.exp(-log_perpl)
    
    # Set processes=1 to avoid fork() warning in multi-threaded environment (UI)
    coherence_model = CoherenceModel(model=lda_model, texts=tokenized_docs, dictionary=dictionary, coherence='c_v', processes=1)
    coherence = coherence_model.get_coherence()
    
    # 6. 產出報告
    vis_data = None
    df_word_dist = pd.DataFrame()
    df_doc_topics = pd.DataFrame()

    if run_viz:
        base_filename = f"{save_prefix}-K{num_topics}" if save_prefix else None
        
        # Set n_jobs=1 to avoid ghost windows in packaged EXE
        try:
            vis_data = gensimvis.prepare(lda_model, corpus_for_lda, dictionary=dictionary, n_jobs=1)
            if save_prefix:
                pyLDAvis.save_html(vis_data, f"{base_filename}-ldavis.html")
        except Exception as e:
            print(f"pyLDAvis failed: {e}")
        
        # b. 詞分佈 (前20名) DataFrame
        topic_words = []
        for t in range(num_topics):
            words = lda_model.show_topic(t, topn=20)
            topic_words.append({
                "主題 (Topic)": f"Topic_{t}",
                "前20詞彙 (Words)": ", ".join([w[0] for w in words]),
                "權重 (Weights)": ", ".join([f"{w[1]:.4f}" for w in words])
            })
        df_word_dist = pd.DataFrame(topic_words)
        if save_prefix:
            df_word_dist.to_csv(f"{base_filename}-word_distribution.csv", index=False, encoding="utf-8-sig")
        
        # c. 主題機率分佈 CSV (每篇文章)
        doc_topics = []
        for idx, doc_bow in enumerate(corpus_for_lda):
            topic_probs = lda_model.get_document_topics(doc_bow, minimum_probability=0)
            probs_dict = {f"Topic_{t}": p for t, p in topic_probs}
            probs_dict["句子 (Document)"] = idx
            doc_topics.append(probs_dict)
            
        df_doc_topics = pd.DataFrame(doc_topics)
        cols = ["句子 (Document)"] + [c for c in df_doc_topics.columns if c != "句子 (Document)"]
        df_doc_topics = df_doc_topics[cols]
        if save_prefix:
            df_doc_topics.to_csv(f"{base_filename}-topics.csv", index=False, encoding="utf-8-sig")
        
        # Generate sankey / relation / heatmap plots
        if save_prefix:
            try:
                ldaSankey(topic_words, f"{base_filename}-relation.html")
                #ldaNetwork(topic_words, f"{base_filename}-network.html")
                if doc_dates:
                    total_rows = len(df_doc_topics)
                    # 確保日期與資料長度一致
                    if len(doc_dates) == total_rows:
                        ldaHeatmap(df_doc_topics, doc_dates, f"{base_filename}-heatmap.png")
                    else:
                        print(f"Heatmap skipped: date length ({len(doc_dates)}) != data length ({total_rows})")
                else:
                    print('no doc date')
            except Exception as e:
                print(f"Visualization failed: {e}")
        
    __ENDMSG = f"Finish Running LDA K={num_topics}"
    print(__ENDMSG)
    return perplexity, coherence, vis_data, df_word_dist, df_doc_topics

def ldaSankey(topic_words, out_html):
    
        
    nodes = []
    links = []
    
    for row in topic_words:
        t_name = row["主題 (Topic)"]
        nodes.append({"name": t_name})
        
        words = row["前20詞彙 (Words)"].split(", ")[:8]
        weights = row["權重 (Weights)"].split(", ")[:8]
        
        for w, wt in zip(words, weights):
            if {"name": w} not in nodes:
                nodes.append({"name": w})
            links.append({"source": t_name, "target": w, "value": max(0.1, float(wt)*100)})
            
    sankey = (
        Sankey(init_opts=opts.InitOpts(width="1200px", height="800px", bg_color="white"))
        .add(
            "Topic-Word Relation",
            nodes,
            links,
            linestyle_opt=opts.LineStyleOpts(opacity=0.3, curve=0.5, color="source"),
            label_opts=opts.LabelOpts(position="right", font_size=12, font_weight="bold"),
            node_gap=15,
        )
        .set_global_opts(title_opts=opts.TitleOpts(title="LDA 主題與高權重詞彙關聯桑基圖 (Top 8)"))
    )
    sankey.render(out_html)

def ldaNetwork(topic_words, out_html):

        
    nodes = []
    links = []
    
    # 統計詞彙出現的主題數量，用來標示「紅色橋接詞」
    word_topic_count = {}
    for row in topic_words:
        words = row["前20詞彙 (Words)"].split(", ")[:15] # 抓稍多一點詞參與網路
        for w in words:
            word_topic_count[w] = word_topic_count.get(w, 0) + 1
            
    # 主題節點樣式
    topic_color_map = ["#1e3a5f", "#3498db", "#e67e22", "#27ae60", "#f1c40f", "#8e44ad", "#7f8c8d", "#d35400"]
    
    for i, row in enumerate(topic_words):
        t_name = row["主題 (Topic)"]
        t_color = topic_color_map[i % len(topic_color_map)]
        
        # 添加主題節點
        nodes.append({
            "name": t_name,
            "symbolSize": 45,
            "itemStyle": {"color": t_color},
            "category": t_name
        })
        
        words = row["前20詞彙 (Words)"].split(", ")[:15] # 提高到前15大詞，讓分支更豐富
        weights = row["權重 (Weights)"].split(", ")[:15]
        
        for w, wt in zip(words, weights):
            # 如果詞已經在 nodes 裡，就不重複加 (但連線要加)
            existing_node = next((n for n in nodes if n["name"] == w), None)
            
            if not existing_node:
                # 判斷是否為橋接詞
                is_bridge = word_topic_count.get(w, 0) > 1
                nodes.append({
                    "name": w,
                    "symbolSize": max(10, float(wt)*150), # 詞點略微縮放
                    "itemStyle": {"color": "#e74c3c" if is_bridge else t_color}, # 橋接詞設為紅色
                    "label": {"show": True}
                })
            
            links.append({
                "source": t_name, 
                "target": w, 
                "value": float(wt),
                "lineStyle": {"width": float(wt) * 100 + 1} # 增加線條粗細
            })
            
    graph = (
        Graph(init_opts=opts.InitOpts(width="1200px", height="1000px", bg_color="white"))
        .add(
            "",
            nodes,
            links,
            repulsion=3000,      
            gravity=0.1,        
            edge_length=100,     # 改回單一數值
            is_draggable=True,
            layout="force",
            linestyle_opts=opts.LineStyleOpts(curve=0.2, opacity=0.5), # 增加一點弧度更像羽翼
            label_opts=opts.LabelOpts(is_show=True, position="right", font_size=10, font_weight="bold"),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(title="LDA 主題與詞彙關聯網絡圖 (樹狀分支版)"),
            legend_opts=opts.LegendOpts(is_show=False)
        )
    )
    graph.render(out_html)

def ldaHeatmap(df_doc_topics, doc_dates, out_png):
    """
    Generate a heatmap of topic probability averages over time (dates).
    """
        
    # 1. 準備數據
    df = df_doc_topics.copy()
    
    # 嘗試將日期轉為 datetime 格式，利於切分與排序
    try:
        df['date_dt'] = pd.to_datetime(doc_dates)
    except:
        # 如果格式極度不符，則給予虛擬序列完成分組
        df['date_dt'] = pd.Series(range(len(df)))

    # 2. 將時間軸依照「評論數量」十等分 (Quantile-based Binning)
    # 使用 pd.qcut 確保每一格中的評論數量大致相同
    try:
        # duplicates='drop' 是防止如果很多評論落在同一秒導致邊界重複
        df['time_bin'] = pd.qcut(df['date_dt'], q=10, duplicates='drop')
        
        # 標籤格式設為兩碼年份 (如: 24-01-01)
        fmt = '%y-%m-%d'

        # 這裡的 interval 可能是 pandas 的 Interval 物件
        def format_interval(interval):
            try:
                start = interval.left.strftime(fmt)
                end = interval.right.strftime(fmt)
                return f"{start}\n~{end}"
            except:
                # 處理備援標籤
                return str(interval)
        
        df['time_label'] = df['time_bin'].apply(format_interval)
    except Exception as e:
        print(f"Heatmap binning fallback due to: {e}")
        # 備援方案：如果日期切分失敗，則按資料索引序號分組
        df['time_label'] = pd.cut(range(len(df)), bins=10, labels=[f"T{i+1}" for i in range(10)])
        # 備援方案：如果日期切分失敗，則按資料索引序號分組
        df['time_label'] = pd.cut(range(len(df)), bins=10, labels=[f"T{i+1}" for i in range(10)])

    # 3. 移除 ID 與中間處理欄位，保留主題機率與新的時間標籤
    topic_cols = [c for c in df.columns if c.startswith('Topic_')]
    heatmap_data = df.groupby('time_label')[topic_cols].mean()
    
    # 確保按照時間順序顯示 (而非字串 ABC 排序)
    # 因為 pd.cut 的 category 本身是有序的，我們可以重新 index
    unique_labels = df.sort_values('date_dt')['time_label'].unique()
    heatmap_data = heatmap_data.reindex(unique_labels)

    # 4. 繪圖
    if heatmap_data.empty:
        return

    plt.figure(figsize=(12, 8))
    # 使用 YlGnBu 漸層色，annot=True 顯示數值
    sns.heatmap(heatmap_data.T, cmap="YlGnBu", annot=True, fmt=".2f", linewidths=.5)
    
    plt.title("LDA Topic Evolution - 10 Time Intervals", fontsize=15, pad=20)
    plt.xlabel("Time Segments", fontsize=12)
    plt.ylabel("Topic Intensity", fontsize=12)
    plt.xticks(rotation=30)
    plt.tight_layout()
    
    # 存檔
    plt.savefig(out_png, dpi=300)
    plt.close()
    print(f"Heatmap (10 bins) saved to {out_png}")