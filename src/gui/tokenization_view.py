from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTabWidget, QFileDialog, QMessageBox, QHeaderView, QLineEdit, QFrame, QSplitter, QListWidget,
    QTextBrowser, QComboBox, QTableWidget, QTableWidgetItem, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QUrl, QTimer
import pandas as pd
import html
from ..core.project_manager import ProjectManager

class TokenizationView(QWidget):
    def __init__(self, project_manager:ProjectManager, update_callback):
        super().__init__()
        self.pm = project_manager
        self.update_callback = update_callback
        self.selected_tokens = []  # List of (sentence_index, token_index)
        
        # State tracking for lazy chunked rendering
        self.chunk_size = 50
        self.loaded_counts = {'tab1': 0, 'tab2': 0}
        self.needs_full_refresh = {'tab1': True, 'tab2': True}
        self._is_loading = False
        
        # Pagination state for Tab 2
        self.current_page = 0
        self.items_per_page = 40

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tab_raw = QWidget() 
        self.tab_edit = QWidget()
        self.tab_export = QWidget() 
        
        self.tabs.addTab(self.tab_raw, "a. 載入與初步結果") 
        self.tabs.addTab(self.tab_edit, "b. 編輯與停用詞設定")
        self.tabs.addTab(self.tab_export, "c. 關鍵詞頻結果") 
        
        self.tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tabs)
        
        self._setup_tab_raw() 
        self.init_tab_edit()
        self._setup_tab_export() 

    def _setup_tab_raw(self): 
        layout = QVBoxLayout(self.tab_raw) 
        # Top controls
        control_layout = QHBoxLayout()
        self.btn_load_csv = QPushButton("載入 CSV / Excel")
        self.btn_load_csv.clicked.connect(self.load_data_file)
        control_layout.addWidget(self.btn_load_csv)
        self.lbl_data_status = QLabel("尚未載入資料")
        control_layout.addWidget(self.lbl_data_status, stretch=1)
        layout.addLayout(control_layout)
        # Single Text Browser for Display
        self.data_browser = QTextBrowser()
        self.data_browser.setOpenLinks(False) 
        self.data_browser.setStyleSheet("QTextBrowser { border: None; background-color: #f7f7f7; color: black; padding: 10px; }")
        layout.addWidget(self.data_browser, stretch=1)

    def init_tab_edit(self):
        layout = QVBoxLayout(self.tab_edit)
        self.edit_splitter = QSplitter(Qt.Orientation.Horizontal)
        compare_widget = QWidget()
        compare_layout = QHBoxLayout(compare_widget)
        compare_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left Panel (Original Data)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_header_widget = QWidget()
        left_header_widget.setFixedHeight(45)
        left_header_layout = QHBoxLayout(left_header_widget)
        left_lbl = QLabel("原始斷詞(唯讀)")
        left_header_layout.addWidget(left_lbl)
        left_layout.addWidget(left_header_widget)
        self.edit_left_browser = QTextBrowser()
        self.edit_left_browser.setOpenLinks(False)
        self.edit_left_browser.setStyleSheet("QTextBrowser { border: 1px solid #ddd; background-color: #ffffff; color: black; padding: 5px;}")
        left_layout.addWidget(self.edit_left_browser)
        compare_layout.addWidget(left_widget, stretch=1)

        # Right Panel (Editable Area)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        tools_widget = QWidget()
        tools_widget.setFixedHeight(45)
        tools_layout = QHBoxLayout(tools_widget)
        right_lbl = QLabel("編輯區:")
        tools_layout.addWidget(right_lbl)
        self.btn_merge = QPushButton("合併[M]")
        self.btn_merge.setStyleSheet("background-color: #ffebee; color: #d32f2f; padding: 2px 4px;")
        self.btn_split = QPushButton("拆詞[D]")
        self.btn_split.setStyleSheet("background-color: #ffebee; color: #d32f2f; padding: 2px 4px;")
        self.btn_mark_stop = QPushButton("停用詞[S]")
        self.btn_mark_stop.setStyleSheet("background-color: #e0e0e0; color: #333333; padding: 2px 4px;")
        self.btn_clear_selection = QPushButton("取消選取[Esc]")
        
        self.btn_merge.clicked.connect(self.merge_selected_tokens)
        self.btn_split.clicked.connect(self.split_selected_token)
        self.btn_mark_stop.clicked.connect(self.mark_selected_as_stop)
        self.btn_clear_selection.clicked.connect(self.clear_selection)
        
        tools_layout.addStretch()
        tools_layout.addWidget(self.btn_clear_selection)
        tools_layout.addWidget(self.btn_split)
        tools_layout.addWidget(self.btn_merge)
        tools_layout.addWidget(self.btn_mark_stop)
        right_layout.addWidget(tools_widget)
        
        self.edit_right_browser = QTextBrowser()
        self.edit_right_browser.setOpenLinks(False)
        self.edit_right_browser.anchorClicked.connect(self._on_anchor_clicked)
        self.edit_right_browser.setStyleSheet("QTextBrowser { border: 1px solid #ddd; background-color: #ffffff; color: black; padding: 5px; }")
        right_layout.addWidget(self.edit_right_browser)
        compare_layout.addWidget(right_widget, stretch=1)
        self.edit_splitter.addWidget(compare_widget)

        # Synchronize scrollbars
        left_v_bar = self.edit_left_browser.verticalScrollBar()
        right_v_bar = self.edit_right_browser.verticalScrollBar()
        if left_v_bar and right_v_bar:
            left_v_bar.valueChanged.connect(right_v_bar.setValue)
            right_v_bar.valueChanged.connect(left_v_bar.setValue)

        # Far Right Panel
        far_right_widget = QFrame()
        far_right_widget.setStyleSheet("""
            QFrame { background-color: #2c2c2c; }
            QLabel { color: white; }
            QLineEdit { background-color: #3d3d3d; color: white; border: 1px solid #555; padding: 3px; }
            QPushButton { background-color: #4a4a4a; color: white; border: 1px solid #666; padding: 4px; }
            QPushButton:hover { background-color: #5a5a5a; }
            QListWidget { background-color: #1e1e1e; color: white; border: 1px solid #3d3d3d; }
        """)
        far_right_layout = QVBoxLayout(far_right_widget)
        far_right_layout.addWidget(QLabel("停用詞列表"))
        self.stop_words_list = QListWidget()
        self.stop_words_list.setStyleSheet("background-color: #1e1e1e; color: white; ")
        far_right_layout.addWidget(self.stop_words_list, stretch=2)
        
        manual_stop_layout = QHBoxLayout()
        self.txt_manual_stop = QLineEdit()
        self.btn_manual_stop = QPushButton("新增")
        self.btn_manual_stop.clicked.connect(self.add_manual_stop_word)
        manual_stop_layout.addWidget(self.txt_manual_stop)
        manual_stop_layout.addWidget(self.btn_manual_stop)
        
        self.btn_import_stop = QPushButton("從txt匯入")
        self.btn_import_stop.clicked.connect(self.import_stop_words_from_txt)
        manual_stop_layout.addWidget(self.btn_import_stop)
        
        far_right_layout.addLayout(manual_stop_layout)
        
        self.btn_delete_stop = QPushButton("刪除[Del]")
        self.btn_delete_stop.clicked.connect(self.delete_selected_stop_words)
        far_right_layout.addWidget(self.btn_delete_stop)
        
        far_right_layout.addWidget(QLabel("已儲存方案"))
        self.scheme_list = QListWidget()
        far_right_layout.addWidget(self.scheme_list, stretch=1)
        self.txt_scheme_name = QLineEdit()
        far_right_layout.addWidget(self.txt_scheme_name)
        self.btn_save_scheme = QPushButton("儲存方案")
        self.btn_save_scheme.clicked.connect(self.save_tokenization_scheme)
        self.btn_load_scheme = QPushButton("載入方案")
        self.btn_load_scheme.clicked.connect(self.load_selected_scheme)
        far_right_layout.addWidget(self.btn_save_scheme)
        far_right_layout.addWidget(self.btn_load_scheme)
        
        self.edit_splitter.addWidget(far_right_widget)
        self.edit_splitter.setSizes([1500, 400])
        layout.addWidget(self.edit_splitter, stretch=1)

        # Pagination Bar
        pagination_widget = QWidget()
        pagination_layout = QHBoxLayout(pagination_widget)
        self.combo_per_page = QComboBox()
        self.combo_per_page.addItems(["20 筆/頁", "40 筆/頁", "100 筆/頁"])
        self.combo_per_page.setCurrentIndex(1)
        self.combo_per_page.currentIndexChanged.connect(self._on_per_page_changed)
        self.btn_prev_page = QPushButton("◀ 上一頁")
        self.btn_prev_page.clicked.connect(self._prev_page)
        self.lbl_page_info = QLabel("第 1 / 1 頁")
        self.btn_next_page = QPushButton("下一頁 ▶")
        self.btn_next_page.clicked.connect(self._next_page)
        pagination_layout.addWidget(QLabel("每頁顯示:"))
        pagination_layout.addWidget(self.combo_per_page)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.btn_prev_page)
        pagination_layout.addWidget(self.lbl_page_info)
        pagination_layout.addWidget(self.btn_next_page)
        layout.addWidget(pagination_widget)

    def _setup_tab_export(self):
        layout = QVBoxLayout(self.tab_export)
        
        # Top controls for export
        export_ctrl_layout = QHBoxLayout()
        self.btn_export_keywords = QPushButton("匯出關鍵字列表 (.txt)")
        self.btn_export_keywords.clicked.connect(self.export_keywords_to_txt)
        export_ctrl_layout.addWidget(self.btn_export_keywords)
        export_ctrl_layout.addStretch()
        layout.addLayout(export_ctrl_layout)

        # 使用 Splitter 讓表格在左，對照內容在右
        self.export_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.export_table = QTableWidget()
        self.export_table.setColumnCount(2)
        self.export_table.setHorizontalHeaderLabels(["關鍵字", "出現頻次"])
        header = self.export_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.export_table.setStyleSheet(" color: black; background-color: white;")
        self.export_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.export_table.itemSelectionChanged.connect(self._on_export_table_selection_changed)
        
        self.export_splitter.addWidget(self.export_table)
        
        self.context_browser = QTextBrowser()
        self.context_browser.setStyleSheet("QTextBrowser { background-color: #f9f9f9; color: black;  padding: 10px; }")
        
        self.export_splitter.addWidget(self.context_browser)
        
        # 設定初始比例 (左側表格較窄，右側內容較寬)
        self.export_splitter.setStretchFactor(0, 1)
        self.export_splitter.setStretchFactor(1, 2)
        
        layout.addWidget(self.export_splitter, stretch=1)

    def load_data_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "選擇資料檔", "", "Excel Files (*.xlsx);;CSV Files (*.csv)")
        if not filepath: return
        try:
            df = pd.read_csv(filepath) if filepath.endswith('.csv') else pd.read_excel(filepath)
            self.pm.loadRawData(df)
            self.lbl_data_status.setText(f"資料已載入 ({len(self.pm.raw_data)} 筆)")
            self.refresh_view()
            self.update_callback()
        except Exception as e:
            QMessageBox.critical(self, "載入失敗", str(e))

    def _restore_scroll_robust(self, bar, value, retries=5):
        """Robustly restore scroll position by retrying until layout completes."""
        if not bar or retries <= 0: return
        bar.setValue(value)
        # 如果 setValue 沒成功 (因為 max 還太小)，就等一下再試一次 (50ms)
        if bar.value() < value and bar.maximum() < value:
            QTimer.singleShot(20, lambda: self._restore_scroll_robust(bar, value, retries - 1))

    def refresh_view(self):
        self.needs_full_refresh = {'tab1': True, 'tab2': True, 'tab3': True}
        self.loaded_counts = {'tab1': 0, 'tab2': 0}
        self._on_tab_changed(self.tabs.currentIndex())

    def clear_selection(self):
        self.selected_tokens = []
        self.needs_full_refresh['tab2'] = True
        self._on_tab_changed(self.tabs.currentIndex(), immediate=True)

    def merge_selected_tokens(self):
        if not self.selected_tokens: return
        sentence_idx = self.selected_tokens[0][0]
        if self.pm.lock[sentence_idx]:
             QMessageBox.warning(self, "錯誤", "該句子已鎖定！")
             return
        token_ids = sorted([t[1] for t in self.selected_tokens])
        msg = self.pm.addMergeWord({sentence_idx: token_ids})
        if msg: QMessageBox.warning(self, "警告", msg)
        self.selected_tokens = []
        self.needs_full_refresh['tab2'] = True
        self._on_tab_changed(self.tabs.currentIndex())
        self.update_callback()

    def split_selected_token(self):
        if not self.selected_tokens: return
        
        # Group by sentence.
        ids_dict = {}
        for s_idx, t_idx in self.selected_tokens:
            if self.pm.lock[s_idx]:
                QMessageBox.warning(self, "錯誤", f"句子 {s_idx} 已鎖定，無法執行操作！")
                return
            if s_idx not in ids_dict: ids_dict[s_idx] = []
            ids_dict[s_idx].append(t_idx)

        # 批次執行拆分
        self.pm.splitWords(ids_dict)
        
        self.selected_tokens = []
        self.needs_full_refresh['tab2'] = True
        self._on_tab_changed(self.tabs.currentIndex())
        self.update_callback()

    def mark_selected_as_stop(self):
        if not self.selected_tokens: return
        ids_dict = {}
        for s, t in self.selected_tokens:
            if s not in ids_dict: ids_dict[s] = []
            ids_dict[s].append(t)
        self.pm.toggleStopwords(ids_dict)
        self.selected_tokens = []
        self.needs_full_refresh['tab2'] = True
        self.needs_full_refresh['tab3'] = True
        self._on_tab_changed(self.tabs.currentIndex())
        self.update_callback()

    def add_manual_stop_word(self):
        word = self.txt_manual_stop.text().strip()
        if word: 
            self.pm.addStopwords(word)
            self.txt_manual_stop.clear()
            self.refresh_view()
            self.update_callback()

    def import_stop_words_from_txt(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "選擇停用詞檔 (.txt)", "", "Text Files (*.txt)")
        if not filepath: return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                words = [line.strip() for line in f if line.strip()]
            if words:
                self.pm.addStopwords(words)
                self.refresh_view()
                self.update_callback()
                QMessageBox.information(self, "成功", f"已從檔案匯入 {len(words)} 個停用詞")
        except Exception as e:
            QMessageBox.critical(self, "匯入失敗", str(e))

    def export_keywords_to_txt(self):
        data = self.pm.getNoneStopWords()
        if not data:
            QMessageBox.warning(self, "警告", "目前沒有關鍵字可供匯出")
            return
            
        filepath, _ = QFileDialog.getSaveFileName(self, "儲存關鍵字列表", "keywords.txt", "Text Files (*.txt)")
        if not filepath: return
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for word, count in data:
                    f.write(f"{word}\n")
            QMessageBox.information(self, "成功", f"關鍵字列表已儲存至 {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "儲存失敗", str(e))

    def delete_selected_stop_words(self):
        selected = self.stop_words_list.selectedItems()
        for item in selected:
            self.pm.removeStopwords(item.text())
        self.refresh_view()
        self.update_callback()

    def lock_sentence(self, s_idx):
        self.pm.lockSentence(s_idx)
        self.needs_full_refresh['tab2'] = True
        self._on_tab_changed(self.tabs.currentIndex(), immediate=True)

    def save_tokenization_scheme(self):
        name = self.txt_scheme_name.text().strip()
        if name:
            self.pm.saveTokenScheme(name)
            self.txt_scheme_name.clear()
            self.refresh_schemes_list()
            self.update_callback()

    def load_selected_scheme(self):
        selected = self.scheme_list.selectedItems()
        if selected:
            self.pm.loadTokenScheme(selected[0].text())
            self.refresh_view()
            self.update_callback()

    def _on_anchor_clicked(self, url: QUrl):
        path = url.toString()
        if path.startswith("lock_"):
            self.lock_sentence(int(path.split('_')[1]))
        elif path.startswith("token_"):
            parts = path.split('_')
            entry = (int(parts[1]), int(parts[2]))
            if entry in self.selected_tokens: self.selected_tokens.remove(entry)
            else: self.selected_tokens.append(entry)
            self.needs_full_refresh['tab2'] = True
            self._on_tab_changed(self.tabs.currentIndex(), immediate=True)

    def _generate_html_chunk(self, token_list, start_idx, end_idx, interactive=False, is_right_pane=False, show_tokens=True):
        if not self.pm.raw_data: return ""
        actual_end = min(len(self.pm.raw_data), end_idx)
        page_html = ""
        for i in range(start_idx, actual_end):
            is_locked = self.pm.lock[i]
            bg = "#ffffff" if i % 2 == 1 else "#f6f6f6"
            page_html += f'<div style="padding: 10px; border-bottom: 2px solid #ddd; background-color: {bg};">'
            lock_icon = "🔒" if is_locked else "🔓"
            
            # Tab 1 (初步結果): 只顯示 ID 與原始文字
            if not show_tokens:
                safe_text = html.escape(str(self.pm.raw_data[i]))
                page_html += f'<div style="color: black;"><b>#{i}</b> {safe_text}</div>'
            else:
                page_html += f'<div><a href="lock_{i}" style="text-decoration:none;">{lock_icon}</a> <b>#{i}</b></div>'
                
            if show_tokens:
                page_html += '<div style="margin-top:5px;">'
                
                # 計算是否為修改過的詞 (與原始資料對比)
                orig_tokens = self.pm.raw_tokenized_data[i]
                orig_set = set(orig_tokens) # 轉成 set 加快查詢速度
                modified_count = 0 
                
                for idx, t in enumerate(token_list[i]):
                    # 精準選紅字邏輯：如果這個詞不在原始分詞結果中，就標為紅色
                    is_modified = False
                    if is_right_pane:
                        if t not in orig_set:
                            is_modified = True

                    is_selected = interactive and (i, idx) in self.selected_tokens
                    is_stop = is_right_pane and t in self.pm.stopwords
                    
                    # 基礎樣式，預設不顯示超連結底線
                    style = "display:inline-block; padding: 3px 8px; margin: 2px; border-radius:10px; border: 1px solid #ccc; text-decoration:none; color:black; "
                    
                    if is_selected: 
                        style += "background-color: #cce5ff; border-color: #66b2ff; font-weight:bold;"
                    elif is_stop: 
                        # 停用詞：改為刪除線，這裡會覆蓋掉前面的 text-decoration:none
                        style += "background-color: #fafafa; border-color: #eeeeee; color: #bbbbbb; text-decoration: line-through;"
                    elif is_modified:
                        # 修改過的詞：紅色背景
                        modified_count += 1
                        red_color = "#ffcdd2" if modified_count % 2 == 1 else "#ef9a9a"
                        style += f"background-color: {red_color}; border-color: #e57373; font-weight:bold;"
                    else: 
                        style += "background-color: #e1f5fe;" if idx % 2 == 0 else "background-color: #fff3e0;"
                    
                    page_html += f'<a href="token_{i}_{idx}" style="{style}">{t}</a>'
                page_html += '</div>'
            page_html += '</div>'
        return page_html

    def _on_tab_changed(self, index, immediate=False):
        if not self.pm.raw_data: return
        
        if index == 0:
            if self.needs_full_refresh['tab1']:
                self.data_browser.setHtml(self._generate_html_chunk(self.pm.raw_tokenized_data, 0, 100, show_tokens=False))
                self.needs_full_refresh['tab1'] = False
                
        elif index == 1:
            if self.needs_full_refresh['tab2']:
                # 紀錄當前的捲軸位置 (增加安全性檢查)
                l_bar_v = self.edit_left_browser.verticalScrollBar()
                r_bar_v = self.edit_right_browser.verticalScrollBar()
                left_scroll = l_bar_v.value() if l_bar_v else 0
                right_scroll = r_bar_v.value() if r_bar_v else 0
                
                start = self.current_page * self.items_per_page
                end = start + self.items_per_page
                
                self.edit_left_browser.setHtml(self._generate_html_chunk(self.pm.raw_tokenized_data, start, end))
                self.edit_right_browser.setHtml(self._generate_html_chunk(self.pm.tokenized_data, start, end, interactive=True, is_right_pane=True))
                
                count = len(self.pm.raw_data)
                max_page = (count + self.items_per_page - 1) // self.items_per_page
                self.lbl_page_info.setText(f"第 {self.current_page+1} / {max_page} 頁")
                self.needs_full_refresh['tab2'] = False
                
                # 採用遞迴強韌還原機制，解決 Layout 異步計算不確定長度的問題
                self._restore_scroll_robust(self.edit_left_browser.verticalScrollBar(), left_scroll)
                self._restore_scroll_robust(self.edit_right_browser.verticalScrollBar(), right_scroll)
            
            self.refresh_stop_words_list()
            self.refresh_schemes_list()
        elif index == 2:
            self.populate_export_table()

    def refresh_stop_words_list(self):
        self.stop_words_list.clear()
        self.stop_words_list.addItems(sorted(self.pm.stopwords))

    def refresh_schemes_list(self):
        self.scheme_list.clear()
        self.scheme_list.addItems(sorted(self.pm.token_schemes.keys()))

    def populate_export_table(self):
        data = self.pm.getNoneStopWords()
        self.export_table.setRowCount(len(data))
        for r, (w, f) in enumerate(data):
            self.export_table.setItem(r, 0, QTableWidgetItem(w))
            self.export_table.setItem(r, 1, QTableWidgetItem(str(f)))

    def _on_export_table_selection_changed(self):
        selected = self.export_table.selectedItems()
        if not selected: return
        word = selected[0].text()
        html = ""
        for i, tokens in enumerate(self.pm.tokenized_data):
            if word in tokens:
                s = "".join([f"<b style='color:red;'>{t}</b>" if t == word else t for t in tokens])
                html += f"<p>#{i} {s}</p>"
        self.context_browser.setHtml(html)

    def _on_per_page_changed(self, i):
        self.items_per_page = [20, 40, 100][i]
        self.current_page = 0
        self.refresh_view()

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_view()

    def _next_page(self):
        if (self.current_page + 1) * self.items_per_page < len(self.pm.raw_data):
            self.current_page += 1
            self.refresh_view()
