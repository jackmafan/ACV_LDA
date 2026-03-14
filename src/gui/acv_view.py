from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QScrollArea, QLineEdit, QSplitter, QFrame, QMessageBox, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from ..core.project_manager import ProjectManager

class ACVView(QWidget):
    """
    ACV (Attributes-Consequences-Values) Analysis View.
    4-Quadrant Layout:
    - Top Left: Category Labeling rows
    - Top Right: Analysis Scheme Management
    - Bottom Left: Word Categorization Table
    - Bottom Right: Word List Loading & Management
    """
    
    # Colors for tags
    COLORS = {
        'A': {'bg': '#e3f2fd', 'fg': '#1565c0'},
        'C': {'bg': '#f3e5f5', 'fg': '#7b1fa2'},
        'V': {'bg': '#fff3e0', 'fg': '#e65100'}
    }
    
    def __init__(self, pm: ProjectManager, parent=None):
        super().__init__(parent)
        self.pm = pm
        self.refresh_callback = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Main Vertical Splitter
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Consistent dark styling for management panels
        side_panel_style = """
            QFrame {
                background-color: #2c2c2c;
                border: 1px solid #444;
                border-radius: 8px;
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
                border-radius: 4px;
            }
            QLineEdit {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #555;
                padding: 4px;
                border-radius: 4px;
            }
            QPushButton {
                background-color: #4a4a4a;
                color: #ffffff;
                border: 1px solid #666;
                padding: 5px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5a5a5a;
            }
        """
        
        # --- Top Half ---
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # Top Left: Category Rows
        self.top_left_widget = QWidget()
        top_left_layout = QVBoxLayout(self.top_left_widget)
        top_left_layout.setContentsMargins(0, 0, 0, 0)
        self.row_a = self._create_category_row("屬性 (Attributes) - A", self.COLORS['A']['bg'], self.COLORS['A']['fg'], "A")
        self.row_c = self._create_category_row("後果 (Consequences) - C", self.COLORS['C']['bg'], self.COLORS['C']['fg'], "C")
        self.row_v = self._create_category_row("價值 (Values) - V", self.COLORS['V']['bg'], self.COLORS['V']['fg'], "V")
        top_left_layout.addWidget(self.row_a)
        top_left_layout.addWidget(self.row_c)
        top_left_layout.addWidget(self.row_v)
        
        # Top Right: Analysis Management (ACV Schemes)
        self.top_right_widget = QFrame()
        self.top_right_widget.setStyleSheet(side_panel_style)
        top_right_layout = QVBoxLayout(self.top_right_widget)
        
        lbl_mgmt = QLabel("ACV 分析方案管理")
        lbl_mgmt.setStyleSheet("font-weight: bold; font-size: 11pt; color: #ffffff;")
        top_right_layout.addWidget(lbl_mgmt)
        
        self.scheme_list = QListWidget()
        top_right_layout.addWidget(self.scheme_list)
        
        scheme_input_layout = QHBoxLayout()
        self.txt_scheme_name = QLineEdit()
        self.txt_scheme_name.setPlaceholderText("新方案名稱...")
        btn_save_scheme = QPushButton("儲存分類")
        btn_save_scheme.clicked.connect(self._on_save_scheme)
        scheme_input_layout.addWidget(self.txt_scheme_name)
        scheme_input_layout.addWidget(btn_save_scheme)
        top_right_layout.addLayout(scheme_input_layout)
        
        scheme_btn_layout = QHBoxLayout()
        btn_load_scheme = QPushButton("載入方案")
        btn_load_scheme.clicked.connect(self._on_load_scheme)
        btn_delete_scheme = QPushButton("刪除")
        btn_delete_scheme.clicked.connect(self._on_delete_scheme)
        scheme_btn_layout.addWidget(btn_load_scheme)
        scheme_btn_layout.addWidget(btn_delete_scheme)
        top_right_layout.addLayout(scheme_btn_layout)
        
        # Add to top splitter
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.addWidget(self.top_left_widget)
        top_splitter.addWidget(self.top_right_widget)
        top_splitter.setStretchFactor(0, 3)
        top_splitter.setStretchFactor(1, 1)
        top_layout.addWidget(top_splitter)
        
        # --- Bottom Half ---
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # Bottom Left: Word Table
        self.bottom_left_widget = QWidget()
        bl_layout = QVBoxLayout(self.bottom_left_widget)
        bl_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_table = QLabel("單詞分類對照表")
        lbl_table.setStyleSheet("font-weight: bold; font-size: 11pt; color: #333;")
        bl_layout.addWidget(lbl_table)
        
        self.word_table = QTableWidget(0, 2)
        self.word_table.setHorizontalHeaderLabels(["單詞 (Word)", "分類 (Category)"])
        self.word_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.word_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.word_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        bl_layout.addWidget(self.word_table)
        
        # Bottom Right: Tokenization Scheme Loading
        self.bottom_right_widget = QFrame()
        self.bottom_right_widget.setStyleSheet(side_panel_style)
        br_layout = QVBoxLayout(self.bottom_right_widget)
        
        lbl_loading = QLabel("載入分詞方案")
        lbl_loading.setStyleSheet("font-weight: bold; font-size: 11pt; color: #ffffff;")
        br_layout.addWidget(lbl_loading)
        
        self.token_scheme_list = QListWidget()
        self.token_scheme_list.setToolTip("選擇一個預先儲存的斷詞方案來載入單詞列表")
        br_layout.addWidget(self.token_scheme_list)
        
        self.btn_load_words = QPushButton("載入所選分詞表")
        self.btn_load_words.setFixedHeight(40)
        self.btn_load_words.setStyleSheet("font-weight: bold; background-color: #2e7d32; color: white;")
        self.btn_load_words.clicked.connect(self._on_load_tokenized_words_from_scheme)
        br_layout.addWidget(self.btn_load_words)
        
        # Add to bottom splitter
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        bottom_splitter.addWidget(self.bottom_left_widget)
        bottom_splitter.addWidget(self.bottom_right_widget)
        bottom_splitter.setStretchFactor(0, 3)
        bottom_splitter.setStretchFactor(1, 1)
        bottom_layout.addWidget(bottom_splitter)
        
        self.main_splitter.addWidget(top_widget)
        self.main_splitter.addWidget(bottom_widget)
        
        main_layout.addWidget(self.main_splitter)

    def _create_category_row(self, title: str, bg_color: str, fg_color: str, cat_id: str) -> QWidget:
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(2, 2, 2, 2)
        
        # Interactive Button instead of just label
        btn_label = QPushButton(f"{cat_id}:")
        btn_label.setToolTip(f"點擊此標籤，將 '{cat_id}' 分類套用到下方所選單詞")
        btn_label.setStyleSheet(f"""
            QPushButton {{
                font-size: 14pt; font-weight: bold; color: {fg_color}; 
                background-color: {bg_color}; border: 2px solid {fg_color};
                border-radius: 5px; min-width: 40px; min-height: 30px;
            }}
            QPushButton:hover {{ background-color: {fg_color}; color: white; }}
        """)
        btn_label.clicked.connect(lambda: self._on_category_clicked(cat_id))
        
        txt_input = QLineEdit()
        txt_input.setPlaceholderText(f"新增...")
        txt_input.setStyleSheet("font-size: 12pt; padding: 2px; max-width: 100px;")
        
        btn_add = QPushButton("新增")
        btn_add.setStyleSheet(f"background-color: {bg_color}; color: {fg_color}; font-weight: bold; padding: 2px 8px; font-size: 10pt;")
        
        row_layout.addWidget(btn_label)
        row_layout.addWidget(txt_input)
        row_layout.addWidget(btn_add)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(50)
        scroll_area.setStyleSheet("background-color: #f7f7f7; border: 1px solid #ddd; border-radius: 4px; margin-left: 5px;")
        
        tags_container = QWidget()
        tags_layout = QHBoxLayout(tags_container)
        tags_layout.setContentsMargins(2, 0, 2, 0)
        tags_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        setattr(self, f"layout_{cat_id}", tags_layout)
        setattr(self, f"input_{cat_id}", txt_input)
        
        btn_add.clicked.connect(lambda: self._on_add_category_word(cat_id))
        txt_input.returnPressed.connect(lambda: self._on_add_category_word(cat_id))
        
        scroll_area.setWidget(tags_container)
        row_layout.addWidget(scroll_area, stretch=1)
        
        return row_widget

    def _create_tag_widget(self, word: str, cat_id: str, index: int) -> QFrame:
        bg_color = self.COLORS[cat_id]['bg']
        fg_color = self.COLORS[cat_id]['fg']
        
        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ background-color: {bg_color}; border: 1px solid {fg_color}; border-radius: 10px; }}")
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(2)
        
        lbl_word = QLabel(f"{cat_id}{index}: {word}")
        lbl_word.setStyleSheet(f"color: {fg_color}; font-size: 12pt; font-weight: bold; border: none;")
        layout.addWidget(lbl_word)
        
        btn_delete = QPushButton("×")
        btn_delete.setFixedSize(20, 20)
        btn_delete.setStyleSheet(f"color: {fg_color}; background-color: transparent; border: none; font-weight: bold; font-size: 12pt;")
        btn_delete.clicked.connect(lambda: self._on_remove_category_word(cat_id, word))
        layout.addWidget(btn_delete)
        
        return frame

    def _on_category_clicked(self, cat_id: str):
        """Assign category to selected word in table."""
        selected_items = self.word_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "未選擇單詞", "請先在下方表格中選擇一個單詞。")
            return
            
        row = selected_items[0].row()
        word = self.word_table.item(row, 0).text()
        
        # Update PM
        # We need to make sure the word is added to the category list
        self.pm.add_acv_word(cat_id, word)
        
        # Also update category_dict word->cat
        self.pm.category_dict[word] = cat_id
        
        # Refresh UI
        self._refresh_category_row(cat_id)
        self.word_table.item(row, 1).setText(cat_id)
        # Style the cell
        self.word_table.item(row, 1).setBackground(Qt.GlobalColor.lightGray)

    def _on_load_tokenized_words_from_scheme(self):
        """Load keywords from the selected tokenization scheme into the table."""
        selected = self.token_scheme_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "未選擇方案", "請在右下角列表選擇一個分詞方案。")
            return
            
        scheme_name = selected.text()
        
        if self.word_table.rowCount() > 0:
            reply = QMessageBox.question(
                self, "覆蓋確認", 
                f"載入方案 '{scheme_name}' 的詞表將會清除目前的顯示，並且「恢復該方案對應的停用詞設定」，是否繼續？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        # We actually need to load the scheme in PM to get its word counts
        try:
            current_acv_dict = self.pm.acv_dict.copy() # Backup ACV state
            current_cat_dict = self.pm.category_dict.copy()
            
            self.pm.load_scheme(scheme_name)
            
            # Restore ACV state as PM.load_scheme might overwrite things if we had schemes for it (though PM currently handles tokens)
            self.pm.acv_dict = current_acv_dict
            self.pm.category_dict = current_cat_dict
            
        except Exception as e:
            QMessageBox.critical(self, "載入失敗", f"無法載入斷詞方案: {str(e)}")
            return

        keywords = self.pm.get_valid_keywords()
        self.word_table.setRowCount(0)
        for word, count in keywords.items():
            row_idx = self.word_table.rowCount()
            self.word_table.insertRow(row_idx)
            
            item_word = QTableWidgetItem(str(word))
            item_word.setFlags(item_word.flags() ^ Qt.ItemFlag.ItemIsEditable)
            
            # Check current mapping
            current_cat = self.pm.category_dict.get(str(word), "")
            item_cat = QTableWidgetItem(current_cat)
            item_cat.setFlags(item_cat.flags() ^ Qt.ItemFlag.ItemIsEditable)
            if current_cat:
                item_cat.setBackground(Qt.GlobalColor.lightGray)
            
            self.word_table.setItem(row_idx, 0, item_word)
            self.word_table.setItem(row_idx, 1, item_cat)
        
        QMessageBox.information(self, "完成", f"已從方案 '{scheme_name}' 載入 {len(keywords)} 個單詞。")
        if self.refresh_callback:
            self.refresh_callback()

    def _on_add_category_word(self, cat_id: str):
        txt_input = getattr(self, f"input_{cat_id}")
        word = txt_input.text().strip()
        if not word: return
        self.pm.add_acv_word(cat_id, word)
        # Also update the table if that word exists there
        for row in range(self.word_table.rowCount()):
            if self.word_table.item(row, 0).text() == word:
                self.word_table.item(row, 1).setText(cat_id)
                self.pm.category_dict[word] = cat_id
                
        txt_input.clear()
        self._refresh_category_row(cat_id)
        
    def _on_remove_category_word(self, cat_id: str, word: str):
        self.pm.remove_acv_word(cat_id, word)
        if self.pm.category_dict.get(word) == cat_id:
            del self.pm.category_dict[word]
            # Update table
            for row in range(self.word_table.rowCount()):
                if self.word_table.item(row, 0).text() == word:
                    self.word_table.item(row, 1).setText("")
                    
        self._refresh_category_row(cat_id)
        
    def _on_save_scheme(self):
        name = self.txt_scheme_name.text().strip()
        if not name:
            QMessageBox.warning(self, "錯誤", "請輸入方案名稱")
            return
        
        # Save current acv_dict and category_dict
        if not hasattr(self.pm, 'acv_schemes'):
            self.pm.acv_schemes = {}
            
        self.pm.acv_schemes[name] = {
            "acv_dict": self.pm.acv_dict.copy(),
            "category_dict": self.pm.category_dict.copy()
        }
        self.txt_scheme_name.clear()
        self._refresh_scheme_list()
        QMessageBox.information(self, "完成", f"方案 '{name}' 已儲存。")

    def _on_load_scheme(self):
        selected = self.scheme_list.currentItem()
        if not selected: return
        name = selected.text()
        
        scheme = self.pm.acv_schemes.get(name)
        if scheme:
            self.pm.acv_dict = scheme["acv_dict"].copy()
            self.pm.category_dict = scheme["category_dict"].copy()
            self.refresh_view()
            # Also update table if it's loaded
            for row in range(self.word_table.rowCount()):
                word = self.word_table.item(row, 0).text()
                self.word_table.item(row, 1).setText(self.pm.category_dict.get(word, ""))
            QMessageBox.information(self, "完成", f"方案 '{name}' 已載入。")

    def _on_delete_scheme(self):
        selected = self.scheme_list.currentItem()
        if not selected: return
        name = selected.text()
        if name in self.pm.acv_schemes:
            del self.pm.acv_schemes[name]
            self._refresh_scheme_list()

    def _refresh_scheme_list(self):
        self.scheme_list.clear()
        self.scheme_list.addItems(self.pm.acv_schemes.keys())

    def _refresh_token_scheme_list(self):
        self.token_scheme_list.clear()
        self.token_scheme_list.addItems(self.pm.schemes.keys())

    def _refresh_category_row(self, cat_id: str):
        layout = getattr(self, f"layout_{cat_id}")
        while layout.count():
            item = layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        words = self.pm.get_acv_words(cat_id)
        for i, word in enumerate(words):
            layout.addWidget(self._create_tag_widget(word, cat_id, i + 1))
        layout.addStretch()

    def refresh_view(self):
        self._refresh_category_row('A')
        self._refresh_category_row('C')
        self._refresh_category_row('V')
        self._refresh_scheme_list()
        self._refresh_token_scheme_list()
