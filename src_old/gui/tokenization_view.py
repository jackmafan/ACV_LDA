from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTabWidget, QFileDialog, QMessageBox, QTableView, QHeaderView,
    QGroupBox, QLineEdit, QScrollArea, QFrame, QSplitter, QListWidget,
    QTextBrowser, QComboBox, QTableWidget, QTableWidgetItem, QAbstractItemView,
    QSpacerItem, QSizePolicy, QGridLayout
)
from PyQt6.QtGui import QShortcut, QKeySequence, QDesktopServices
from PyQt6.QtCore import Qt, QUrl, QTimer
import pandas as pd
from ..core.project_manager import ProjectManager
from .flow_layout import FlowLayout
#from .token_widget import TokenWidget

class TokenizationView(QWidget):
    def __init__(self, project_manager, update_callback):
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
        self.tab_raw = QWidget() # Renamed from tab_load
        self.tab_edit = QWidget()
        self.tab_export = QWidget() # Added new tab widget
        
        self.tabs.addTab(self.tab_raw, "1. 載入與初步結果") # Updated tab title
        self.tabs.addTab(self.tab_edit, "2. 編輯與停用詞設定")
        self.tabs.addTab(self.tab_export, "3. 關鍵詞頻結果") # Added new tab
        
        self.tabs.currentChanged.connect(self._on_tab_changed)
        
        layout.addWidget(self.tabs)
        
        self._setup_tab_raw() # Renamed from init_tab_load
        self.init_tab_edit()
        self._setup_tab_export() # Call to setup the new tab

    def _setup_tab_raw(self): # Renamed from init_tab_load
        layout = QVBoxLayout(self.tab_raw) # Changed to self.tab_raw

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
        self.data_browser.setOpenLinks(False) # We will handle clicks manually
        self.data_browser.setStyleSheet("QTextBrowser { border: None; background-color: #f7f7f7; font-size: 14pt; padding: 10px; }")
        
        layout.addWidget(self.data_browser, stretch=1)

    def init_tab_edit(self):
        layout = QVBoxLayout(self.tab_edit)

        # Main horizontal splitter
        self.edit_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Compare Widget to lock 1:1 ratio firmly
        compare_widget = QWidget()
        compare_layout = QHBoxLayout(compare_widget)
        compare_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left Panel (Original Read-only Data)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        left_header_widget = QWidget()
        left_header_widget.setFixedHeight(45)
        left_header_layout = QHBoxLayout(left_header_widget)
        left_header_layout.setContentsMargins(0, 0, 0, 0)
        left_lbl = QLabel("原始斷詞(唯讀)")
        left_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        left_header_layout.addWidget(left_lbl)
        left_header_layout.addStretch()
        left_layout.addWidget(left_header_widget)
        
        self.edit_left_browser = QTextBrowser()
        self.edit_left_browser.setOpenLinks(False)
        self.edit_left_browser.setStyleSheet("QTextBrowser { border: 1px solid #ddd; background-color: #ffffff; padding: 5px; font-size: 13pt; }")
        left_layout.addWidget(self.edit_left_browser)
        compare_layout.addWidget(left_widget, stretch=1)

        # Right Panel (Editable Active Data)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Tools row for interactions
        tools_widget = QWidget()
        tools_widget.setFixedHeight(45)
        tools_layout = QHBoxLayout(tools_widget)
        tools_layout.setContentsMargins(0, 0, 0, 0)
        right_lbl = QLabel("編輯區:")
        right_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        tools_layout.addWidget(right_lbl)
        self.btn_merge = QPushButton("合併[M]")
        self.btn_merge.setStyleSheet("font-size: 10pt; background-color: #ffebee; color: #d32f2f; padding: 2px 4px;")
        
        self.btn_force_merge = QPushButton("強制合併[F]")
        self.btn_force_merge.setStyleSheet("font-size: 10pt; background-color: #ffebee; color: #d32f2f; padding: 2px 4px;")
        
        self.btn_split = QPushButton("拆詞[D]")
        self.btn_split.setStyleSheet("font-size: 10pt; background-color: #ffebee; color: #d32f2f; padding: 2px 4px;")
        
        self.btn_mark_stop = QPushButton("停用詞[S]")
        self.btn_mark_stop.setStyleSheet("font-size: 10pt; background-color: #e0e0e0; color: #333333; padding: 2px 4px;")
        
        self.btn_clear_selection = QPushButton("取消選取[Esc]")
        self.btn_clear_selection.setStyleSheet("font-size: 10pt; background-color: #e0e0e0; color: #333333; padding: 2px 4px;")
        
        self.btn_merge.clicked.connect(self.merge_selected_tokens)
        self.btn_force_merge.clicked.connect(self.force_local_merge_selected_tokens)
        self.btn_split.clicked.connect(self.split_selected_token)
        self.btn_mark_stop.clicked.connect(self.mark_selected_as_stop)
        self.btn_clear_selection.clicked.connect(self.clear_selection)
        
        tools_layout.addStretch()
        tools_layout.addWidget(self.btn_clear_selection)
        tools_layout.addWidget(self.btn_split)
        tools_layout.addWidget(self.btn_merge)
        tools_layout.addWidget(self.btn_force_merge)
        tools_layout.addWidget(self.btn_mark_stop)
        right_layout.addWidget(tools_widget)
        
        self.edit_right_browser = QTextBrowser()
        self.edit_right_browser.setOpenLinks(False)
        self.edit_right_browser.anchorClicked.connect(self._on_anchor_clicked)
        self.edit_right_browser.setStyleSheet("QTextBrowser { border: 1px solid #ddd; background-color: #ffffff; padding: 5px; font-size: 13pt; }")
        right_layout.addWidget(self.edit_right_browser)
        compare_layout.addWidget(right_widget, stretch=1)
        
        self.edit_splitter.addWidget(compare_widget)

        # Synchronize scrollbars between left and right editable panes
        left_sb = self.edit_left_browser.verticalScrollBar()
        right_sb = self.edit_right_browser.verticalScrollBar()
        left_sb.valueChanged.connect(lambda val: right_sb.setValue(val) if right_sb.value() != val else None)
        right_sb.valueChanged.connect(lambda val: left_sb.setValue(val) if left_sb.value() != val else None)
        
        left_hsb = self.edit_left_browser.horizontalScrollBar()
        right_hsb = self.edit_right_browser.horizontalScrollBar()
        left_hsb.valueChanged.connect(lambda val: right_hsb.setValue(val) if right_hsb.value() != val else None)
        right_hsb.valueChanged.connect(lambda val: left_hsb.setValue(val) if left_hsb.value() != val else None)

        # Far Right Panel (Stop Words & Schemes)
        far_right_widget = QFrame()
        far_right_widget.setStyleSheet("""
            QFrame {
                background-color: #2c2c2c;
                border-left: 1px solid #444;
            }
            QLabel {
                color: #ffffff;
                border: none;
                background-color: transparent;
            }
            QListWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
            }
            QLineEdit {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #555;
            }
            QPushButton {
                background-color: #4a4a4a;
                color: #ffffff;
                border: 1px solid #666;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
        """)
        far_right_layout = QVBoxLayout(far_right_widget)
        lbl_stop = QLabel("停用詞列表")
        lbl_stop.setStyleSheet("font-weight: bold; color: #ffffff;")
        far_right_layout.addWidget(lbl_stop)
        
        self.stop_words_list = QListWidget()
        self.stop_words_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.stop_words_list.setStyleSheet("font-size: 14pt;")
        far_right_layout.addWidget(self.stop_words_list, stretch=5)
        
        # Manual Stop Word Input
        manual_stop_layout = QHBoxLayout()
        self.txt_manual_stop = QLineEdit()
        self.txt_manual_stop.setPlaceholderText("新增停用詞...")
        self.txt_manual_stop.setStyleSheet("padding: 5px; font-size: 11pt;")
        self.btn_manual_stop = QPushButton("新增")
        self.btn_manual_stop.setStyleSheet("font-size: 10pt; padding: 5px;")
        
        self.txt_manual_stop.returnPressed.connect(self.add_manual_stop_word)
        self.btn_manual_stop.clicked.connect(self.add_manual_stop_word)
        
        manual_stop_layout.addWidget(self.txt_manual_stop, stretch=1)
        manual_stop_layout.addWidget(self.btn_manual_stop)
        
        far_right_layout.addLayout(manual_stop_layout)
        
        self.btn_delete_stop = QPushButton("刪除[Del]")
        self.btn_delete_stop.setStyleSheet("font-size: 10pt; padding: 5px;")
        self.btn_delete_stop.clicked.connect(self.delete_selected_stop_words)
        far_right_layout.addWidget(self.btn_delete_stop)
        
        self.btn_import_stops = QPushButton("從 TXT 匯入...")
        self.btn_import_stops.setStyleSheet("font-size: 10pt; padding: 5px;")
        self.btn_import_stops.clicked.connect(self.import_stop_words)
        far_right_layout.addWidget(self.btn_import_stops)
        
        # Shortcut for Stop Words List
        self.shortcut_del_stop = QShortcut(QKeySequence(Qt.Key.Key_Delete), self.stop_words_list)
        self.shortcut_del_stop.activated.connect(self.delete_selected_stop_words)
        
        # Spacer
        far_right_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))
        
        # Scheme Management (Relocated from Tab 3)
        lbl_scheme = QLabel("已儲存的斷詞方案")
        lbl_scheme.setStyleSheet("font-weight: bold; font-size: 13pt; color: #ffffff;")
        far_right_layout.addWidget(lbl_scheme)
        
        self.scheme_list = QListWidget()
        self.scheme_list.setStyleSheet("font-size: 12pt;")
        far_right_layout.addWidget(self.scheme_list, stretch=2)
        
        self.txt_scheme_name = QLineEdit()
        self.txt_scheme_name.setPlaceholderText("輸入新方案名稱...")
        self.txt_scheme_name.setStyleSheet("font-size: 11pt;")
        far_right_layout.addWidget(self.txt_scheme_name)
        
        scheme_btn_layout = QGridLayout()
        self.btn_save_scheme = QPushButton("儲存")
        self.btn_save_scheme.setStyleSheet("font-weight: bold; ")
        self.btn_save_scheme.clicked.connect(self.save_tokenization_scheme)
        
        self.btn_load_scheme = QPushButton("載入")
        self.btn_load_scheme.setStyleSheet("font-weight: bold; ")
        self.btn_load_scheme.clicked.connect(self.load_selected_scheme)
        
        self.btn_delete_scheme = QPushButton("刪除")
        self.btn_delete_scheme.clicked.connect(self.delete_selected_scheme)
        
        scheme_btn_layout.addWidget(self.btn_save_scheme, 0, 0)
        scheme_btn_layout.addWidget(self.btn_load_scheme, 0, 1)
        scheme_btn_layout.addWidget(self.btn_delete_scheme, 1, 0, 1, 2)
        far_right_layout.addLayout(scheme_btn_layout)
        
        self.edit_splitter.addWidget(far_right_widget)
        
        # Shortcuts for Tab 2
        self.shortcut_merge = QShortcut(QKeySequence("M"), self.tab_edit)
        self.shortcut_merge.activated.connect(self.merge_selected_tokens)
        self.shortcut_force_merge = QShortcut(QKeySequence("F"), self.tab_edit)
        self.shortcut_force_merge.activated.connect(self.force_local_merge_selected_tokens)
        self.shortcut_split = QShortcut(QKeySequence("D"), self.tab_edit)
        self.shortcut_split.activated.connect(self.split_selected_token)
        self.shortcut_stop = QShortcut(QKeySequence("S"), self.tab_edit)
        self.shortcut_stop.activated.connect(self.mark_selected_as_stop)
        self.shortcut_lock = QShortcut(QKeySequence("L"), self.tab_edit)
        self.shortcut_lock.activated.connect(self.toggle_lock_selected)
        self.shortcut_clear = QShortcut(QKeySequence(Qt.Key.Key_Escape), self.tab_edit)
        self.shortcut_clear.activated.connect(self.clear_selection)
        
        # Set Splitter Proportions
        # Compare Widget gets rigid 50/50, so we just size it against Stop Words panel (1: 0.2 ratio)
        self.edit_splitter.setStretchFactor(0, 10) # Compare Widget
        self.edit_splitter.setStretchFactor(1, 2)  # Far Right
        self.edit_splitter.setSizes([1000, 200])
        
        layout.addWidget(self.edit_splitter, stretch=1)
        
        # Pagination UI Control Bar
        pagination_widget = QWidget()
        pagination_layout = QHBoxLayout(pagination_widget)
        pagination_layout.setContentsMargins(10, 5, 10, 5)
        
        self.combo_per_page = QComboBox()
        self.combo_per_page.addItems(["20 筆/頁", "40 筆/頁", "100 筆/頁"])
        self.combo_per_page.setCurrentIndex(1) # Default to 40
        self.combo_per_page.setStyleSheet("padding: 2px; font-size: 11pt;")
        self.combo_per_page.currentIndexChanged.connect(self._on_per_page_changed)
        
        self.btn_prev_page = QPushButton("◀ 上一頁")
        self.btn_prev_page.setStyleSheet("padding: 5px; font-size: 11pt;")
        self.btn_prev_page.clicked.connect(self._prev_page)
        self.btn_prev_page.setEnabled(False)
        
        self.lbl_page_info = QLabel("第 1 / 1 頁")
        self.lbl_page_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_page_info.setStyleSheet("font-size: 11pt; font-weight: bold;")
        self.lbl_page_info.setMinimumWidth(100)
        
        self.btn_next_page = QPushButton("下一頁 ▶")
        self.btn_next_page.setStyleSheet("padding: 5px; font-size: 11pt;")
        self.btn_next_page.clicked.connect(self._next_page)
        self.btn_next_page.setEnabled(False)
        
        pagination_layout.addWidget(QLabel("每頁顯示:"))
        pagination_layout.addWidget(self.combo_per_page)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.btn_prev_page)
        pagination_layout.addWidget(self.lbl_page_info)
        pagination_layout.addWidget(self.btn_next_page)
        pagination_layout.addStretch()
        
        layout.addWidget(pagination_widget)

    def _setup_tab_export(self):
        layout = QVBoxLayout(self.tab_export)
        
        # Top toolbar
        toolbar = QHBoxLayout()
        lbl = QLabel("有效關鍵字與詞頻統計:")
        lbl.setStyleSheet("font-weight: bold; font-size: 16pt;")
        toolbar.addWidget(lbl)
        toolbar.addStretch()
        
        self.btn_export_txt = QPushButton("匯出 keywords (.txt)")
        self.btn_export_txt.setStyleSheet("background-color: #e3f2fd; color: #1565c0; padding: 5px;")
        self.btn_export_txt.clicked.connect(self.export_keywords_txt)
        toolbar.addWidget(self.btn_export_txt)
        
        lbl_hint = QLabel("(頻次由高到低)")
        lbl_hint.setStyleSheet("font-size: 11pt; color: gray;")
        toolbar.addWidget(lbl_hint)
        
        layout.addLayout(toolbar)
        
        # Main Splitter for Tab 3
        self.export_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Side: Table Area
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        self.export_table = QTableWidget()
        self.export_table.setColumnCount(2)
        self.export_table.setHorizontalHeaderLabels(["關鍵字 (Keyword)", "出現頻次 (Frequency)"])
        self.export_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.export_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.export_table.setStyleSheet("font-size: 14pt;")
        self.export_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.export_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.export_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.export_table.itemSelectionChanged.connect(self._on_export_table_selection_changed)
        
        table_layout.addWidget(self.export_table)
        self.export_splitter.addWidget(table_widget)
        
        # Right Side: Context Viewer
        context_widget = QWidget()
        context_layout = QVBoxLayout(context_widget)
        context_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_context = QLabel("檢視該詞彙出現的原始句子:")
        lbl_context.setStyleSheet("font-weight: bold; font-size: 14pt; color: #333;")
        context_layout.addWidget(lbl_context)
        
        self.context_browser = QTextBrowser()
        self.context_browser.setStyleSheet("QTextBrowser { border: 1px solid #ddd; background-color: #fafafa; color: #000000; padding: 10px; font-size: 16pt; }")
        context_layout.addWidget(self.context_browser)
        
        self.export_splitter.addWidget(context_widget)
        
        # # Right Side: Context Viewer
        # context_widget = QWidget()
        # context_layout = QVBoxLayout(context_widget)
        # context_layout.setContentsMargins(0, 0, 0, 0)
        
        # lbl_context = QLabel("檢視該詞彙出現的原始句子:")
        # lbl_context.setStyleSheet("font-weight: bold; font-size: 14pt; color: #333;")
        # context_layout.addWidget(lbl_context)
        
        # self.context_browser = QTextBrowser()
        # self.context_browser.setStyleSheet("QTextBrowser { border: 1px solid #ddd; background-color: #fafafa; color: #000000; padding: 10px; font-size: 16pt; }")
        # context_layout.addWidget(self.context_browser)
        
        # self.export_splitter.addWidget(context_widget)
        
        # Set splitter sizes (e.g., 30% table, 70% context)
        self.export_splitter.setStretchFactor(0, 3)
        self.export_splitter.setStretchFactor(1, 7)
        self.export_splitter.setSizes([300, 700])
        
        layout.addWidget(self.export_splitter, stretch=1)

    def load_data_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "選擇資料檔", "", "Excel Files (*.xlsx);;CSV Files (*.csv);;All Files (*)"
        )
        if not filepath:
            return

        try:
            if filepath.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
                
            # Auto-detect text column
            text_col = None
            for col in ['Comments', 'comment', 'Text', 'text']:
                if col in df.columns:
                    text_col = col
                    break
                    
            if not text_col and len(df.columns) > 0:
                text_col = df.columns[0]
                
            self.pm.load_raw_data(df, text_col)
            self.lbl_data_status.setText(f"已載入欄位: {text_col}")
            
            self.selected_tokens = [] # Reset selection
            self.refresh_view() # Use refresh_view to reset pagination
            self.update_callback() # Notify main app that data is loaded
            
        except Exception as e:
            QMessageBox.critical(self, "載入失敗", str(e))

    def clear_selection(self):
        """Clear all currently selected tokens."""
        if self.selected_tokens:
            self.selected_tokens = []
            self.needs_full_refresh['tab2'] = True
            self._on_tab_changed(self.tabs.currentIndex(), immediate=True)

    def merge_selected_tokens(self):
        """Merge selected tokens into a single word."""
        if not self.selected_tokens:
            return
            
        # Group by sentence. We only support merging inside the SAME sentence at a time.
        sentence_idx = self.selected_tokens[0][0]
        for s_idx, t_idx in self.selected_tokens:
            if s_idx != sentence_idx:
                QMessageBox.warning(self, "錯誤", "只能合併同一個句子內相鄰的詞彙！")
                return
                
        if hasattr(self.pm, 'locked_sentences') and sentence_idx in self.pm.locked_sentences:
            QMessageBox.warning(self, "錯誤", "這個句子已經被「鎖定🔒」，無法在上面進行拆詞或合併。請先解鎖！")
            self.selected_tokens = []
            self.needs_full_refresh['tab2'] = True
            self._on_tab_changed(self.tabs.currentIndex())
            return
                
        # Get the words directly from the current active tokenized data
        tokens = list(self.pm.tokenized_data.iloc[sentence_idx])
        indices = sorted([t_idx for s, t_idx in self.selected_tokens])
        
        # Ensure they are adjacent
        for i in range(len(indices) - 1):
            if indices[i+1] - indices[i] != 1:
                QMessageBox.warning(self, "錯誤", "請選擇『相鄰』的詞彙進行合併！")
                return
                
        merged_word = "".join([tokens[i] for i in indices])
        
        self.pm.merge_tokens_local_and_global(sentence_idx, indices, merged_word)
        self.selected_tokens = []
        
        # Refresh both panes
        self.needs_full_refresh['tab2'] = True
        self._on_tab_changed(self.tabs.currentIndex())
        self.update_callback()

    def force_local_merge_selected_tokens(self):
        """Force merge selected tokens into a single word locally without global dictionary updates."""
        if not self.selected_tokens:
            return
            
        sentence_idx = self.selected_tokens[0][0]
        
        if hasattr(self.pm, 'locked_sentences') and sentence_idx in self.pm.locked_sentences:
            QMessageBox.warning(self, "錯誤", "這個句子已經被「鎖定🔒」，無法在上面進行拆詞或合併。請先解鎖！")
            self.selected_tokens = []
            self.needs_full_refresh['tab2'] = True
            self._on_tab_changed(self.tabs.currentIndex())
            return
            
        for s_idx, t_idx in self.selected_tokens:
            if s_idx != sentence_idx:
                QMessageBox.warning(self, "錯誤", "只能合併同一個句子內相鄰的詞彙！")
                return
                
        tokens = list(self.pm.tokenized_data.iloc[sentence_idx])
        indices = sorted([t_idx for s, t_idx in self.selected_tokens])
        
        # Ensure they are adjacent
        for i in range(len(indices) - 1):
            if indices[i+1] - indices[i] != 1:
                QMessageBox.warning(self, "錯誤", "請選擇『相鄰』的詞彙進行合併！")
                return
                
        merged_word = "".join([tokens[i] for i in indices])
        
        self.pm.force_local_merge(sentence_idx, indices, merged_word)
        self.selected_tokens = []
        
        # Refresh both panes
        self.needs_full_refresh['tab2'] = True
        self._on_tab_changed(self.tabs.currentIndex())
        self.update_callback()

    def split_selected_token(self):
        """Split a selected token into characters (local editing)."""
        if not self.selected_tokens:
            return
            
        if len(self.selected_tokens) > 1:
            QMessageBox.warning(self, "錯誤", "一次只能選擇一個詞彙進行拆詞！")
            return
            
        sentence_idx, token_idx = self.selected_tokens[0]
        
        if hasattr(self.pm, 'locked_sentences') and sentence_idx in self.pm.locked_sentences:
            QMessageBox.warning(self, "錯誤", "這個句子已經被「鎖定🔒」，無法在上面進行拆詞或合併。請先解鎖！")
            self.selected_tokens = []
            self.needs_full_refresh['tab2'] = True
            self._on_tab_changed(self.tabs.currentIndex())
            return
        
        # Validation checks
        tokens = list(self.pm.tokenized_data.iloc[sentence_idx])
        if len(tokens[token_idx]) <= 1:
            QMessageBox.warning(self, "錯誤", "該詞彙已經是單一字元，無法再拆分！")
            return
            
        self.pm.split_token(sentence_idx, token_idx)
        self.selected_tokens = []
        self.needs_full_refresh['tab2'] = True
        self._on_tab_changed(self.tabs.currentIndex())
        self.update_callback()

    def toggle_lock_selected(self):
        """Toggle lock state of the sentence of the currently selected token."""
        if not self.selected_tokens:
            return
        sentence_idx = self.selected_tokens[0][0]
        self.pm.toggle_lock(sentence_idx)
        self.selected_tokens = []
        self.needs_full_refresh['tab2'] = True
        self._on_tab_changed(self.tabs.currentIndex(), immediate=True)
        self.update_callback()

    def mark_selected_as_stop(self):
        """Toggle stop word status for selected tokens."""
        if not self.selected_tokens:
            return
            
        for s_idx, t_idx in self.selected_tokens:
            tokens = list(self.pm.tokenized_data.iloc[s_idx])
            word = tokens[t_idx]
            if word in self.pm.tokenizer.stop_words:
                self.pm.remove_stop_word(word)
            else:
                self.pm.add_stop_word(word)
            
        self.selected_tokens = []
        self.needs_full_refresh['tab2'] = True
        self.needs_full_refresh['tab3'] = True
        self._on_tab_changed(self.tabs.currentIndex())
        self.update_callback()

    def add_manual_stop_word(self):
        """Add a stop word manually from the right panel text input."""
        word = self.txt_manual_stop.text().strip()
        if not word:
            return
            
        self.pm.add_stop_word(word)
        self.txt_manual_stop.clear()
        
        self.needs_full_refresh['tab2'] = True
        self.needs_full_refresh['tab3'] = True
        self._on_tab_changed(self.tabs.currentIndex())
        self.update_callback()

    def import_stop_words(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "選擇停用詞檔案", "", "Text Files (*.txt);;All Files (*)"
        )
        if not filepath:
            return
        try:
            self.pm.load_stop_words_from_file(filepath)
            self.selected_tokens = []
            self.needs_full_refresh['tab2'] = True
            self._on_tab_changed(self.tabs.currentIndex())
            self.update_callback()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"無法載入檔案: {str(e)}")

    def delete_selected_stop_words(self):
        """Remove selected stop words from the dictionary."""
        selected_items = self.stop_words_list.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            word = item.text()
            self.pm.remove_stop_word(word)
            
        self.needs_full_refresh['tab2'] = True
        self.needs_full_refresh['tab3'] = True
        self._on_tab_changed(self.tabs.currentIndex())
        self.update_callback()

    def _on_anchor_clicked(self, url: QUrl):
        """Handle token click in the interactive HTML view."""
        path = url.toString()
        
        if path.startswith("lock_"):
            try:
                parts = path.split('_')
                s_idx = int(parts[1])
                self.pm.toggle_lock(s_idx)
                self.selected_tokens = []
                self.needs_full_refresh['tab2'] = True
                self._on_tab_changed(self.tabs.currentIndex(), immediate=True)
            except Exception as e:
                print(f"Error toggling lock: {e}")
            return
            
        if not path.startswith("token_"):
            return
            
        try:
            # path is format: token_s_idx_t_idx
            parts = path.split('_')
            s_idx = int(parts[1])
            t_idx = int(parts[2])
            entry = (s_idx, t_idx)
            
            if entry in self.selected_tokens:
                self.selected_tokens.remove(entry)
            else:
                self.selected_tokens.append(entry)
                
            # Full refresh of Tab 2 Left HTML to reflect selection changes
            self.needs_full_refresh['tab2'] = True
            # Use immediate=True for simple selection to avoid flicker
            self._on_tab_changed(self.tabs.currentIndex(), immediate=True)
        except Exception as e:
            print(f"Error parsing token click: {e}")

    def _generate_html_chunk(self, token_series, start_idx, end_idx, interactive=False, is_right_pane=False, show_raw_text=True, show_tokens=True):
        """Generate an HTML string for a chunk of sentences."""
        if self.pm.raw_data is None or token_series is None:
            return ""
            
        raw_series = self.pm.raw_data[self.pm.text_column]
        actual_end = min(len(raw_series), end_idx)
        
        html = ""
        
        for i in range(start_idx, actual_end):
            tokens = list(token_series.iloc[i])
            raw_text = str(raw_series.iloc[i]).replace('\n', ' ').replace('\r', '') if show_raw_text else ""
            
            # Container block with seamless alternating background
            bg_container = "#ffffff" if i % 2 == 1 else "#f6f6f6" # Tab 1/2 start with Gray (index 0)
            html += f'<div style="padding: 15px; border-bottom: 20px solid #d0d0d0; background-color: {bg_container};">'
            
            is_locked = hasattr(self.pm, 'locked_sentences') and i in self.pm.locked_sentences
            lock_icon = "🔒" if is_locked else "🔓"
            lock_color = "#d32f2f" if is_locked else "#cccccc"
            
            if show_raw_text:
                if interactive:
                    html += f'<div style="margin-bottom: 10px;">' \
                            f'<a href="lock_{i}" style="text-decoration: none; font-size: 16pt; color: {lock_color}; margin-right: 8px;">{lock_icon}</a>' \
                            f'<span style="font-size: 14pt; font-weight: bold; color: #444444;">{raw_text}</span></div>'
                else:
                    html += f'<div style="margin-bottom: 10px;"><span style="font-size: 14pt; font-weight: bold; color: #444444;">{raw_text}</span></div>'
            elif interactive:
                html += f'<div style="margin-bottom: 5px;">' \
                        f'<a href="lock_{i}" style="text-decoration: none; font-size: 14pt; color: {lock_color}; margin-right: 8px;">{lock_icon}</a>' \
                        f'</div>'
            else:
                html += f'<div style="margin-bottom: 5px;">' \
                        f'<span style="font-size: 14pt; color: {lock_color}; margin-right: 8px;">{lock_icon}</span>' \
                        f'</div>'
            
            if show_tokens:
                # Tokens
                html += '<div style="line-height: 1.5;">'
                
                # Retrieve original tokens for comparison if we are generating for the right pane
                if is_right_pane and self.pm.original_tokenized_data is not None and i < len(self.pm.original_tokenized_data):
                    orig_tokens = list(self.pm.original_tokenized_data.iloc[i])
                else:
                    orig_tokens = []
                    
                for idx, token in enumerate(tokens):
                    is_edited = is_right_pane and (token not in orig_tokens)
                    is_selected = interactive and (i, idx) in self.selected_tokens
                    
                    if is_edited: # Alternating Reds for edited
                        if idx % 2 == 0:
                            bg_color = "#ffebee" # Light Red 1
                            border_color = "#ffcdd2"
                            text_color = "#d32f2f"
                        else:
                            bg_color = '#ffebee'  # bg_color = "#fce4ec" # Light Pink 2
                            border_color = "#f8bbd0" 
                            text_color = "#c2185b"
                        font_weight = "bold"
                        text_decoration = "none"
                    else: # Default style (Alternating Blue/Orange)
                        if idx % 2 == 0:
                            bg_color = "#e1f5fe" # Light blue
                            border_color = "#b3e5fc"
                            text_color = "#333333"
                        else:
                            bg_color = "#fff3e0" # Light orange
                            border_color = "#ffe0b2"
                            text_color = "#333333"
                        font_weight = "normal"
                        text_decoration = "none"
                    
                    # Stop words override
                    if is_right_pane and token in self.pm.tokenizer.stop_words:
                        bg_color = "#fafafa" # Very faded gray
                        border_color = "#eeeeee"
                        text_color = "#bbbbbb" # Faded text
                        text_decoration = "line-through"
                        font_weight = "normal"
                        
                    # Selection override
                    if is_selected:
                        bg_color = "#cce5ff"
                        border_color = "#66b2ff"
                        text_color = "#0055cc"
                        text_decoration = "none"
                        font_weight = "bold"
                        
                    style = f"background-color: {bg_color}; color: {text_color}; border: 1px solid {border_color}; " \
                            f"border-radius: 12px; padding: 4px 10px; margin-right: 8px; margin-bottom: 8px; " \
                            f"font-size: 14pt; font-weight: {font_weight}; text-decoration: {text_decoration}; " \
                            f"display: inline-block; white-space: nowrap;"
                            
                    html += f'<a href="token_{i}_{idx}" style="{style}">{token}</a> '
                    
                html += '</div>'
            html += '</div>'
            
        return html

    def _on_per_page_changed(self, index):
        options = [20, 40, 100]
        self.items_per_page = options[index]
        self.current_page = 0
        self.selected_tokens = []
        self.needs_full_refresh['tab2'] = True
        self._on_tab_changed(self.tabs.currentIndex())
        
    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.selected_tokens = []
            self.needs_full_refresh['tab2'] = True
            self._on_tab_changed(self.tabs.currentIndex())
            
    def _next_page(self):
        if self.pm.raw_data is None:
            return
        max_page = max(0, (len(self.pm.raw_data) - 1) // self.items_per_page)
        if self.current_page < max_page:
            self.current_page += 1
            self.selected_tokens = []
            self.needs_full_refresh['tab2'] = True
            self._on_tab_changed(self.tabs.currentIndex())

    def _load_chunk(self, tab_id, preserve_scroll=False):
        """Loads the HTML chunk for the requested tab."""
        if self.pm.raw_data is None:
            return
            
        total_items = len(self.pm.raw_data)
            
        if tab_id == 'tab1':
            start_idx = self.loaded_counts[tab_id]
            if start_idx >= total_items:
                return # Fully loaded
            # Load ALL at once for Tab 1 as requested by user
            html = self._generate_html_chunk(self.pm.original_tokenized_data, 0, total_items, interactive=False, is_right_pane=False, show_raw_text=True, show_tokens=False)
            self.data_browser.setHtml(html) # Changed to setHtml for full load
            self.loaded_counts[tab_id] = total_items
        elif tab_id in ('tab2_left', 'tab2_right', 'tab2'):
            start_idx = self.current_page * self.items_per_page
            end_idx = min(start_idx + self.items_per_page, total_items)
            
            # Left pane shows original tokenized data, not interactive
            html_left = self._generate_html_chunk(self.pm.original_tokenized_data, start_idx, end_idx, interactive=False, is_right_pane=False, show_raw_text=False)
            self.edit_left_browser.setHtml(html_left)
            
            # Right pane shows tokenized data, interactive
            html_right = self._generate_html_chunk(self.pm.tokenized_data, start_idx, end_idx, interactive=True, is_right_pane=True, show_raw_text=False)
            self.edit_right_browser.setHtml(html_right)
            
            self.loaded_counts['tab2'] = end_idx
            
            # Update pagination UI
            max_page = max(1, (total_items + self.items_per_page - 1) // self.items_per_page)
            self.lbl_page_info.setText(f"第 {self.current_page + 1} / {max_page} 頁")
            self.btn_prev_page.setEnabled(self.current_page > 0)
            self.btn_next_page.setEnabled(self.current_page < max_page - 1)
        elif tab_id == 'tab3':
            # This tab will be populated with keyword data, not chunks of sentences
            # So, no _generate_html_chunk call here.
            # Instead, we'll call a specific method to populate the table.
            self.populate_export_table()
            self.needs_full_refresh['tab3'] = False

    def _on_tab_changed(self, index, immediate=False):
        """Lazy load the views based on which tab is active to improve UI performance."""
        if self.pm.raw_data is None:
            return
            
        if index == 0: # Tab 1: Raw data and initial tokenization
            if self.needs_full_refresh['tab1']:
                self.data_browser.clear() # Clear before loading all
                self.loaded_counts['tab1'] = 0
                self._load_chunk('tab1')
                self.needs_full_refresh['tab1'] = False
                
        elif index == 1: # Tab 2: Edit and Stop words
            if self.needs_full_refresh['tab2']:
                preserve = self.loaded_counts['tab2'] > 0
                
                # Save scroll position if preserving
                scroll_pos = 0
                if preserve:
                    scroll_pos = self.edit_left_browser.verticalScrollBar().value()
                    
                # Note: self.edit_left_browser.setHtml() clears everything anyway
                self._load_chunk('tab2', preserve_scroll=preserve)
                
                # Handle scroll restoration
                if preserve:
                    if immediate:
                        # For simple selection, immediate restore prevents flicker
                        self.edit_left_browser.verticalScrollBar().setValue(scroll_pos)
                    else:
                        # For content changes (merge/split), defer slightly to allow layout to finish
                        QTimer.singleShot(10, lambda: self.edit_left_browser.verticalScrollBar().setValue(scroll_pos))
                    
                self.needs_full_refresh['tab2'] = False
                
            self.refresh_stop_words_list()
        
        elif index == 2: # Tab 3: Export
            if self.needs_full_refresh['tab3']:
                self._load_chunk('tab3') # This will call populate_export_table
                self.needs_full_refresh['tab3'] = False
            self.refresh_schemes_list()

    def refresh_view(self):
        """Called by app.py when completely new data is loaded or project state changes."""
        # Status tracking
        self.needs_full_refresh = {'tab1': True, 'tab2': True, 'tab3': True}
        self.loaded_counts = {'tab1': 0, 'tab2': 0, 'tab3': 0}
        
        if self.pm.text_column:
            self.lbl_data_status.setText(f"已載入欄位: {self.pm.text_column}")
        else:
            self.lbl_data_status.setText("尚未載入資料")
            
        self._on_tab_changed(self.tabs.currentIndex())
        self.refresh_schemes_list()
        self.refresh_stop_words_list()



    def populate_export_table(self):
        """Populate the Tab 3 table with valid keywords and their frequencies."""
        if self.pm.tokenized_data is None:
            return
            
        valid_counts = self.pm.get_valid_keywords()
        self.export_table.setRowCount(len(valid_counts))
        self.export_table.setSortingEnabled(False) # Disable sorting while populating
        
        for row, (word, count) in enumerate(valid_counts.items()):
            item_word = QTableWidgetItem(str(word))
            
            # Important: Set data as integer for proper numerical sorting later if enabled
            item_count = QTableWidgetItem()
            item_count.setData(Qt.ItemDataRole.DisplayRole, int(count))
            item_count.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self.export_table.setItem(row, 0, item_word)
            self.export_table.setItem(row, 1, item_count)

    def export_keywords_txt(self):
        """Export the valid keywords to a text file."""
        if self.pm.tokenized_data is None:
            QMessageBox.warning(self, "警告", "沒有可輸出的資料！")
            return
            
        filepath, _ = QFileDialog.getSaveFileName(
            self, "儲存關鍵字 (txt)", "", "Text Files (*.txt)"
        )
        if not filepath:
            return
            
        try:
            valid_counts = self.pm.get_valid_keywords()
            with open(filepath, 'w', encoding='utf-8') as f:
                for word in valid_counts.index:
                    f.write(f"{word}\n")
            QMessageBox.information(self, "成功", f"成功匯出 {len(valid_counts)} 個關鍵字至:\n{filepath}\n\n推薦用法: '可以把它們 copy 下來到前面再刪除 (停用詞)'")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"匯出失敗: {str(e)}")
    def _on_export_table_selection_changed(self):
        """Update the context viewer when a keyword is selected."""
        selected_items = self.export_table.selectedItems()
        if not selected_items:
            self.context_browser.clear()
            return
            
        keyword = selected_items[0].text()
        self._show_keyword_context(keyword)
        
    def _show_keyword_context(self, keyword):
        """Find original sentences containing the keyword and render them."""
        if self.pm.tokenized_data is None:
            return
            
        #html = f"<h3>關鍵字：<span style='color: #d32f2f; background-color: #ffebee; padding: 2px 5px;'>{keyword}</span></h3><hr/>"
        html = f""
        count = 0
        for i, tokens in enumerate(self.pm.tokenized_data):
            # Check if the keyword exists in the token list for this sentence
            if keyword in tokens:
                count += 1
                
                # Reconstruct the original text by joining tokens
                sentence_text = ""
                for t in tokens:
                    if t == keyword:
                        # Highlight the keyword
                        sentence_text += f"<span style='color: #000000; background-color: #ffcdd2; font-weight: bold;'>{t}</span>"
                    else:
                        sentence_text += f"<span>{t}</span>"
                        
                html += f"<p><b>[{i}]</b> {sentence_text}</p>"
                
                # Cap the output to prevent lag on super common words
                if count >= 100:
                    html += "<p style='color: gray;'>... (僅顯示前 100 筆)</p>"
                    break
                    
        self.context_browser.setHtml(html)
        
    def refresh_schemes_list(self):
        """Update the list of saved schemes."""
        self.scheme_list.clear()
        if hasattr(self.pm, 'schemes'):
            for scheme in sorted(self.pm.schemes.keys()):
                self.scheme_list.addItem(scheme)

    def refresh_stop_words_list(self):
        """Update the UI list of stop words."""
        self.stop_words_list.clear()
        if hasattr(self.pm.tokenizer, 'stop_words'):
            for sw in sorted(self.pm.tokenizer.stop_words):
                self.stop_words_list.addItem(sw)

    def save_tokenization_scheme(self):
        """Save the current tokenization state as a named scheme."""
        if self.pm.tokenized_data is None:
            QMessageBox.warning(self, "警告", "目前沒有斷詞結果可以儲存！")
            return
            
        name = self.txt_scheme_name.text().strip()
        if not name:
            QMessageBox.warning(self, "警告", "請先輸入要儲存的方案名稱！")
            self.txt_scheme_name.setFocus()
            return
            
        try:
            self.pm.save_scheme(name)
            self.txt_scheme_name.clear()
            self.refresh_schemes_list()
            QMessageBox.information(self, "成功", f"成功儲存斷詞方案: {name}\n\n這將在您下次儲存專案 (Save Project) 時一併被寫入 .aproj！\n(將來這會解鎖 ACV/LDA 分析)")
            self.update_callback() # Notify main app of state change
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"儲存方案失敗: {str(e)}")

    def load_selected_scheme(self):
        """Load the selected tokenization scheme."""
        selected_items = self.scheme_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "請先從清單中選擇一個方案！")
            return
            
        name = selected_items[0].text()
        
        reply = QMessageBox.question(
            self, '確認載入',
            f"確定要載入方案 '{name}' 嗎？\n這將會覆蓋您目前介面上的所有斷詞修改！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.pm.load_scheme(name)
                # Need to refresh EVERYTHING
                self.needs_full_refresh = {k: True for k in self.needs_full_refresh}
                self.refresh_stop_words_list()
                self._on_tab_changed(self.tabs.currentIndex())
                self.update_callback()
                QMessageBox.information(self, "成功", f"方案 '{name}' 載入成功！")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"載入方案失敗: {str(e)}")

    def delete_selected_scheme(self):
        """Delete the selected tokenization scheme."""
        selected_items = self.scheme_list.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            name = item.text()
            self.pm.delete_scheme(name)
            
        self.refresh_schemes_list()
        self.update_callback()
