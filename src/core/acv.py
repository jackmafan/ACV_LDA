import pandas as pd
import matplotlib.backends.backend_pdf # Ensure PyInstaller includes PDF backend
import matplotlib.patches as patches
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib as mpl
import sys

# Ok
def acvMatrix(ACV_token_scheme, acv_dict, word2acvlabel):

    if not ACV_token_scheme or 'tokenized_data' not in ACV_token_scheme:
        return pd.DataFrame()

    a_lbls = acv_dict['A']['labels']
    c_lbls = acv_dict['C']['labels']
    v_lbls = acv_dict['V']['labels']
    
    row_headers = a_lbls + c_lbls
    col_headers = c_lbls + v_lbls
    
    matrix = pd.DataFrame(0.0, index=row_headers, columns=col_headers)
    
    for tokens in ACV_token_scheme['tokenized_data']:
        if not tokens: continue
        
        # Map tokens to their labels
        sentence_labels = []
        for word in tokens:
            label = word2acvlabel.get(word)
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


def acvImage(ACV_token_scheme, acv_dict, word2acvlabel, chosen_labels: list[list[str]], save_path: str):
    
    if sys.platform.startswith('win'):
        mpl.rcParams['font.sans-serif'] = ['Microsoft JhengHei', 'SimHei', 'Arial Unicode MS']
    elif sys.platform == 'darwin':
        mpl.rcParams['font.sans-serif'] = ['AppleGothic', 'PingFang HK', 'Heiti TC']
    else:
        mpl.rcParams['font.sans-serif'] = ['Noto Sans CJK TC', 'Noto Sans CJK JP', 'AR PL UMing TW', 'WenQuanYi Micro Hei', 'DejaVu Sans']
    mpl.rcParams['axes.unicode_minus'] = False
    
    matrix = acvMatrix(ACV_token_scheme, acv_dict, word2acvlabel)
    if matrix.empty:
        return False
    
    # Traverse actually connected labels in current set
    A_labels, C_labels, V_labels = chosen_labels
    edges = []
    for a_lbl in A_labels:
        for c_lbl in C_labels:
            if c_lbl in matrix.columns and a_lbl in matrix.index:
                val = matrix.at[a_lbl, c_lbl]
                if val > 0:
                    edges.append((a_lbl, c_lbl, val))
                    
    for c_lbl in C_labels:
        for v_lbl in V_labels:
            if v_lbl in matrix.columns and c_lbl in matrix.index:
                val = matrix.at[c_lbl, v_lbl]
                if val > 0:
                    edges.append((c_lbl, v_lbl, val))
                    
    connected_A = set()
    connected_C = set()
    connected_V = set()
    for src, dst, val in edges:
        if src in A_labels: connected_A.add(src)
        if src in C_labels: connected_C.add(src)
        if dst in C_labels: connected_C.add(dst)
        if dst in V_labels: connected_V.add(dst)
        
    if not edges:
        return False
                    
    G = nx.DiGraph()
    
    # 準備節點放入 G 中，並指派 layer
    for node in connected_A:
        _serial, _display = node.split('-', 1)[0], node.split('-', 1)[1]
        G.add_node(node, layer=0, label=f"{_serial}\n{_display}")
        
    for node in connected_C:
        _serial, _display = node.split('-', 1)[0], node.split('-', 1)[1]
        G.add_node(node, layer=1, label=f"{_serial}\n{_display}")
        
    for node in connected_V:
        _serial, _display = node.split('-', 1)[0], node.split('-', 1)[1]
        G.add_node(node, layer=2, label=f"{_serial}\n{_display}")
        
    max_val = max([val for src, dst, val in edges]) if edges else 1.0
    for src, dst, val in edges:
        G.add_edge(src, dst, weight=val)
        
    # 計算各節點的座標：A 在下 (y=0), C 在中 (y=1), V 在上 (y=2)
    pos = {}
    
    def set_x(nodes, y_level):
        # 排序節點名稱，讓它們有固定的左右順序
        n_list = sorted(list(nodes))
        n = len(n_list)
        if n == 0: return
        spacing = 1.0
        start_x = - (n - 1) * spacing / 2.0
        for i, node in enumerate(n_list):
            pos[node] = (start_x + i * spacing, y_level)
            
    set_x(connected_A, 0)
    set_x(connected_C, 1)
    set_x(connected_V, 2)
    
    # 圖表大小隨節點數量自動延展
    max_nodes = max(len(connected_A), len(connected_C), len(connected_V))
    fig_width = max(10, max_nodes * 1.5)
    plt.figure(figsize=(fig_width, 8), dpi=200)
    ax = plt.gca()
    
    
    # 統一文字方塊尺寸
    box_w = 0.80
    box_h = 0.24
    
    # 計算邊界交點函數，確保連線剛好停在方塊邊緣並有完美箭頭
    def get_intersect(x1, y1, x2, y2, bw, bh):
        dx = x2 - x1
        dy = y2 - y1
        if dx == 0 and dy == 0: return x1, y1, x2, y2
        ry = (bh / 2) / abs(dy) if dy != 0 else float('inf')
        rx = (bw / 2) / abs(dx) if dx != 0 else float('inf')
        r = min(rx, ry)
        return x1 + dx * r, y1 + dy * r, x2 - dx * r, y2 - dy * r

    # 畫連線 (使用自定義 FancyArrowPatch 以對齊矩形邊框)
    max_val = max([val for _, _, val in edges]) if edges else 1.0
    for src, dst, val in edges:
        x1, y1 = pos[src]
        x2, y2 = pos[dst]
        sx, sy, ex, ey = get_intersect(x1, y1, x2, y2, box_w, box_h)
        
        width = max(0.5, (val / max_val) * 4.0)
        arrow = patches.FancyArrowPatch((sx, sy), (ex, ey),
                                        arrowstyle='-|>,head_length=8,head_width=4',
                                        linewidth=width, color='#34495e',
                                        zorder=1, alpha=0.9)
        ax.add_patch(arrow)

    # 畫統一尺寸節點文字與方框
    for node in G.nodes:
        x, y = pos[node]
        layer = G.nodes[node]['layer']
        
        # 依照階層上色：V為深灰，C為淺灰，A為白底
        if layer == 2:
            fc = '#888888'
            tc = 'white'
        elif layer == 1:
            fc = '#e8e8e8'
            tc = 'black'
        else:
            fc = '#ffffff'
            tc = 'black'
            
        rect = patches.Rectangle((x - box_w/2, y - box_h/2), box_w, box_h,
                                 linewidth=1.2, edgecolor='black', facecolor=fc, zorder=2)
        ax.add_patch(rect)
        
        ax.text(x, y, G.nodes[node]['label'], color=tc,
                ha='center', va='center', fontsize=11, fontweight='bold', zorder=3)
    
    # 畫連線權重文字
    edge_labels = {(u, v): f"{G[u][v]['weight']:.2f}" for u, v in G.edges()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8, label_pos=0.3, 
                                 bbox=dict(facecolor='white', alpha=0.9, edgecolor='none', pad=0.5), ax=ax)
    
    # 設定留白空間，避免被切掉
    plt.margins(0.1, 0.1)
    plt.axis('off')
    plt.tight_layout()
    
    fmt = save_path.split('.')[-1].lower() if '.' in save_path else 'pdf'
    
    try:
        plt.savefig(save_path, format=fmt, bbox_inches='tight', transparent=False, facecolor='white')
        plt.close()
        return True
    except Exception as e:
        plt.close()
        raise e
