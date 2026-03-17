from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QScrollArea, QLineEdit, QSplitter, QFrame, QMessageBox, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QAbstractItemView, QTabWidget, QFileDialog
)
from typing import Dict, List
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont
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
        
        self.tabs = QTabWidget()
        
        # --- Tab 1: Category Labeling Management ---
        self.tab_tagging = QWidget()
        tagging_layout = QVBoxLayout(self.tab_tagging)
        
        # Main Vertical Splitter (moved inside tab)
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
        
        tagging_layout.addWidget(self.main_splitter)
        
        # --- Tab 2: Analysis Results (Implication Matrix) ---
        self.tab_analysis = QWidget()
        analysis_main_layout = QVBoxLayout(self.tab_analysis)
        analysis_main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_hint = QLabel("<b>共現分析與蘊含矩陣 (Implication Matrix)</b>")
        lbl_hint.setStyleSheet("font-size: 14pt; margin-bottom: 20px;")
        analysis_main_layout.addWidget(lbl_hint)
        
        self.btn_export_matrix = QPushButton("輸出蘊含矩陣 (.csv)")
        self.btn_export_matrix.setFixedSize(300, 60)
        self.btn_export_matrix.setStyleSheet("background-color: #2c3e50; font-weight: bold; font-size: 12pt; color: white; border-radius: 8px;")
        self.btn_export_matrix.clicked.connect(self._on_export_matrix)
        analysis_main_layout.addWidget(self.btn_export_matrix)
        
        analysis_main_layout.addStretch()
        
        self.tabs.addTab(self.tab_analysis, "2. 關聯分析分析")
        
        main_layout.addWidget(self.tabs)

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
        
        btn_add = QPushButton("新增標籤")
        btn_add.setStyleSheet(f"background-color: {bg_color}; color: {fg_color}; font-weight: bold; padding: 2px 8px; font-size: 10pt;")
        btn_add.setToolTip("建立一個新的 ACV 概念分類（標籤）")
        
        row_layout.addWidget(btn_label)
        row_layout.addWidget(txt_input)
        row_layout.addWidget(btn_add)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(50)
        #scroll_area.setStyleSheet(" border: 1px solid #ddd; border-radius: 4px; margin-left: 5px;")
        
        tags_container = QWidget()
        tags_layout = QHBoxLayout(tags_container)
        tags_layout.setContentsMargins(2, 0, 2, 0)
        tags_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        setattr(self, f"layout_{cat_id}", tags_layout)
        setattr(self, f"input_{cat_id}", txt_input)
        
        btn_add.clicked.connect(lambda: self._on_add_category_label(cat_id))
        txt_input.returnPressed.connect(lambda: self._on_add_category_label(cat_id))
        
        scroll_area.setWidget(tags_container)
        row_layout.addWidget(scroll_area, stretch=1)
        
        return row_widget

    def _create_tag_widget(self, label: str, cat_id: str, index: int) -> QFrame:
        bg_color = self.COLORS[cat_id]['bg']
        fg_color = self.COLORS[cat_id]['fg']
        
        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ background-color: {bg_color}; border: 1px solid {fg_color}; border-radius: 10px; }}")
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(2)
        
        # Clickable Label Name
        btn_label = QPushButton(f"{label}")
        btn_label.setStyleSheet(f"color: {fg_color}; font-size: 12pt; font-weight: bold; border: none; background: transparent;")
        btn_label.setToolTip(f"點擊此標籤，將下方表格中選取的單詞歸類為「{label}」")
        btn_label.clicked.connect(lambda: self._on_tag_clicked(cat_id, label))
        layout.addWidget(btn_label)
        
        btn_delete = QPushButton("×")
        btn_delete.setFixedSize(20, 20)
        btn_delete.setStyleSheet(f"color: {fg_color}; background-color: transparent; border: none; font-weight: bold; font-size: 12pt;")
        btn_delete.clicked.connect(lambda: self._on_remove_category_label(cat_id, label))
        layout.addWidget(btn_delete)
        
        return frame

    def _on_tag_clicked(self, cat_id: str, label: str):
        """Assign the selected word in the table to this label."""
        selected_items = self.word_table.selectedItems()
        if not selected_items:
            # Check if we can find selection by current row if no items are strictly 'selectedItems' (Qt quirk)
            row = self.word_table.currentRow()
            if row < 0:
                QMessageBox.warning(self, "未選擇單詞", "請先在下方表格中選擇一個要分類的單詞。")
                return
        else:
            row = selected_items[0].row()
            
        word = self.word_table.item(row, 0).text()
        
        # Update PM
        self.pm.assign_word_to_label(cat_id, label, word)
        
        # Refresh UI table row
        self.word_table.item(row, 1).setText(label)
        self.word_table.item(row, 1).setBackground(Qt.GlobalColor.lightGray)
        # Category specific coloring for the text in table
        self.word_table.item(row, 1).setForeground(Qt.GlobalColor.black)

    def _on_category_clicked(self, cat_id: str):
        """Previously used to assign category directly, now just a hint or unassign?"""
        # For now, let's make it 'Unassign' the word from any label
        selected_items = self.word_table.selectedItems()
        if not selected_items: return
            
        row = selected_items[0].row()
        word = self.word_table.item(row, 0).text()
        
        self.pm.unassign_word(word)
        self.word_table.item(row, 1).setText("")
        self.word_table.item(row, 1).setBackground(Qt.GlobalColor.white)

    def _update_word_table(self, keywords: Dict[str, int]):
        """Populate the table with given keywords and current ACV mapping."""
        self.word_table.setRowCount(0)
        # Update active state in PM for auto-save support
        self.pm.active_acv_keywords = dict(keywords) if hasattr(keywords, 'items') else {}
        
        # keywords might be pd.Series or Dict
        if hasattr(keywords, 'items'):
            items = keywords.items()
        else:
            items = [] # Fallback
            
        for word, count in items:
            row_idx = self.word_table.rowCount()
            self.word_table.insertRow(row_idx)
            
            item_word = QTableWidgetItem(str(word))
            item_word.setFlags(item_word.flags() ^ Qt.ItemFlag.ItemIsEditable)
            
            # Check current mapping
            info = self.pm.category_dict.get(str(word), {})
            display_text = ""
            if isinstance(info, dict):
                display_text = info.get("label", "")
            
            item_cat = QTableWidgetItem(display_text)
            item_cat.setFlags(item_cat.flags() ^ Qt.ItemFlag.ItemIsEditable)
            if display_text:
                item_cat.setBackground(Qt.GlobalColor.lightGray)
            
            self.word_table.setItem(row_idx, 0, item_word)
            self.word_table.setItem(row_idx, 1, item_cat)

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

        # We need to temporarily load the scheme in PM to calculate its current valid keywords
        try:
            current_acv_dict = self.pm.acv_dict.copy()
            current_cat_dict = self.pm.category_dict.copy()
            
            self.pm.load_scheme(scheme_name)
            keywords = self.pm.get_valid_keywords()
            
            # Capture snapshot for ACV consistency
            if self.pm.tokenized_data is not None:
                self.pm.acv_tokenized_snapshot = [list(tokens) for tokens in self.pm.tokenized_data]
            
            self.pm.acv_dict = current_acv_dict
            self.pm.category_dict = current_cat_dict
            
            self._update_word_table(keywords)
            
        except Exception as e:
            QMessageBox.critical(self, "載入失敗", f"無法載入斷詞方案: {str(e)}")
            return
        
        QMessageBox.information(self, "完成", f"已從方案 '{scheme_name}' 載入 {len(keywords)} 個單詞。")
        #self._refresh_v_list()
        if self.refresh_callback:
            self.refresh_callback()

    def _on_add_category_label(self, cat_id: str):
        txt_input = getattr(self, f"input_{cat_id}")
        label = txt_input.text().strip()
        if not label: return
        self.pm.add_acv_label(cat_id, label)
        txt_input.clear()
        self._refresh_category_row(cat_id)
        
    def _on_remove_category_label(self, cat_id: str, label: str):
        reply = QMessageBox.question(self, "刪除標籤", f"是否確定要刪除標籤「{label}」？此操作會取消所有單詞對此標籤的連結。", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No: return
        
        self.pm.remove_acv_label(cat_id, label)
        # Update table for all words that were assigned to this label
        for row in range(self.word_table.rowCount()):
            if self.word_table.item(row, 1).text() == label:
                self.word_table.item(row, 1).setText("")
                self.word_table.item(row, 1).setBackground(Qt.GlobalColor.white)
                    
        self._refresh_category_row(cat_id)
        
    def _on_save_scheme(self):
        name = self.txt_scheme_name.text().strip()
        if not name:
            QMessageBox.warning(self, "錯誤", "請輸入方案名稱")
            return
        
        # 1. Collect words currently in table
        keyword_counts = {}
        for row in range(self.word_table.rowCount()):
            word = self.word_table.item(row, 0).text()
            # We don't strictly need counts for ACV matching, but it's good for restoration
            keyword_counts[word] = 0 
            
        # 2. Save nested structure via PM
        self.pm.save_acv_scheme(name, keyword_counts)
        
        self.txt_scheme_name.clear()
        self._refresh_scheme_list()
        QMessageBox.information(self, "完成", f"方案 '{name}' 已儲存。")

    def _on_load_scheme(self):
        selected = self.scheme_list.currentItem()
        if not selected: return
        name = selected.text()
        
        try:
            keyword_counts = self.pm.load_acv_scheme(name)
            self.refresh_view()
            # Update table with the keywords that were saved in the ACV scheme
            if keyword_counts:
                self._update_word_table(keyword_counts)
            
            QMessageBox.information(self, "完成", f"方案 '{name}' 已載入。")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "載入失敗", f"無法載入 ACV 方案: {str(e)}")

    def _on_delete_scheme(self):
        selected = self.scheme_list.currentItem()
        if not selected: return
        name = selected.text()
        if name in self.pm.acv_schemes:
            del self.pm.acv_schemes[name]
            if self.pm.current_acv_scheme == name:
                self.pm.current_acv_scheme = None
            self._refresh_scheme_list()

    def _refresh_scheme_list(self):
        self.scheme_list.clear()
        self.scheme_list.addItems(self.pm.acv_schemes.keys())

    def _on_export_matrix(self):
        """Handle the co-occurrence matrix calculation and export."""
        if self.pm.tokenized_data is None:
            QMessageBox.warning(self, "警告", "尚未載入任何分詞數據（請先到分詞介面執行分詞或載入），無法分析。")
            return
            
        try:
            # 1. Calculate Matrix
            matrix_df = self.pm.calculate_acv_matrix()
            
            # 2. File save dialog
            file_path, _ = QFileDialog.getSaveFileName(
                self, "儲存蘊含矩陣", "", "CSV Files (*.csv)"
            )
            
            if file_path:
                if not file_path.endswith('.csv'):
                    file_path += '.csv'
                
                # Export to CSV with UTF-8-SIG for Excel compatibility
                matrix_df.to_csv(file_path, encoding='utf-8-sig')
                QMessageBox.information(self, "成功", f"蘊含矩陣已成功匯出至：\n{file_path}")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "錯誤", f"匯出失敗：{str(e)}")

    def _refresh_token_scheme_list(self):
        self.token_scheme_list.clear()
        self.token_scheme_list.addItems(self.pm.schemes.keys())

    def _refresh_category_row(self, cat_id: str):
        layout = getattr(self, f"layout_{cat_id}")
        while layout.count():
            item = layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        labels = self.pm.get_acv_labels(cat_id)
        for i, label in enumerate(labels):
            layout.addWidget(self._create_tag_widget(label, cat_id, i + 1))
        layout.addStretch()

    def refresh_view(self):
        """Update tags and scheme list."""
        self._refresh_category_row('A')
        self._refresh_category_row('C')
        self._refresh_category_row('V')
        self._refresh_scheme_list()
        self._refresh_token_scheme_list()
        
        # Auto-restore words if table is empty but PM has active keywords
        if self.word_table.rowCount() == 0 and self.pm.active_acv_keywords:
            self._update_word_table(self.pm.active_acv_keywords)
