import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QScrollArea, QLineEdit, QSplitter, QFrame, QMessageBox, QSizePolicy,
    QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QAbstractItemView, QTabWidget, QFileDialog
)
from typing import Dict, List
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QFont
from src_new.core.project_manager import ProjectManager

class ACVView(QWidget):
    """
    ACV (Attributes-Consequences-Values) Analysis View for the new architecture.
    """
    
    COLORS = {
        'A': {'bg': '#1e3a5f', 'fg': '#90caf9'}, # Dark theme friendly colors
        'C': {'bg': '#3c1e5f', 'fg': '#ce93d8'},
        'V': {'bg': '#5f2c1e', 'fg': '#ffb74d'}
    }
    
    def __init__(self, pm: ProjectManager, parent=None):
        super().__init__(parent)
        self.pm = pm
        self.acv_ui_refs = {} # 用於存儲 A/C/V 相關的 UI 元件引用
        self.init_ui()
        self.refresh_view() # Ensure initial state is loaded

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        
        # --- Tab 1: Category Labeling Management ---
        self.tab_tagging = QWidget()
        tagging_layout = QVBoxLayout(self.tab_tagging)
        
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Styling for panels
        side_panel_style = """
            QFrame {
                background-color: #2c2c2c;
                border: 1px solid #444;
                border-radius: 8px;
            }
            QLabel { color: #ffffff; border: none; background-color: transparent; }
            QListWidget, QTableWidget {
                background-color: #1e1e1e; color: #ffffff;
                border: 1px solid #3d3d3d; border-radius: 4px;
            }
            QLineEdit {
                background-color: #3d3d3d; color: #ffffff;
                border: 1px solid #555; padding: 4px; border-radius: 4px;
            }
            QPushButton {
                background-color: #4a4a4a; color: #ffffff;
                border: 1px solid #666; padding: 5px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #5a5a5a; }
        """
        
        # --- Top Half ---
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        self.row_a = self._create_category_row("A", "屬性 (Attributes)")
        self.row_c = self._create_category_row("C", "後果 (Consequences)")
        self.row_v = self._create_category_row("V", "價值 (Values)")
        top_layout.addWidget(self.row_a)
        top_layout.addWidget(self.row_c)
        top_layout.addWidget(self.row_v)
        
        # --- Bottom Half ---
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        # Bottom Left: Word Table
        self.bottom_left_widget = QWidget()
        bl_layout = QVBoxLayout(self.bottom_left_widget)
        bl_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_table = QLabel("單詞分類對照表 (點擊上方標籤可進行分類)")
        lbl_table.setStyleSheet("font-weight: bold; font-size: 11pt; color: white;")
        bl_layout.addWidget(lbl_table)
        
        self.word_table = QTableWidget(0, 2)
        self.word_table.setHorizontalHeaderLabels(["單詞 (Word)", "分類 (Category)"])
        header = self.word_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.word_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.word_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.word_table.setStyleSheet(side_panel_style)
        bl_layout.addWidget(self.word_table)
        
        # Bottom Right: Tokenization Scheme Loading
        self.bottom_right_widget = QFrame()
        self.bottom_right_widget.setStyleSheet(side_panel_style)
        br_layout = QVBoxLayout(self.bottom_right_widget)
        
        lbl_loading = QLabel("載入分詞方案以列出高頻單詞")
        lbl_loading.setStyleSheet("font-weight: bold; font-size: 11pt; color: #ffffff;")
        br_layout.addWidget(lbl_loading)
        
        self.token_scheme_list = QListWidget()
        self.token_scheme_list.setToolTip("選擇一個預先儲存的斷詞方案來載入單詞列表")
        br_layout.addWidget(self.token_scheme_list)
        
        self.btn_load_words = QPushButton("載入所選分詞表")
        self.btn_load_words.setFixedHeight(40)
        self.btn_load_words.setStyleSheet("font-weight: bold; background-color: #2e7d32; color: white;")
        self.btn_load_words.clicked.connect(self._on_load_token_scheme)
        br_layout.addWidget(self.btn_load_words)
        
        bottom_splitter = QSplitter(Qt.Orientation.Horizontal)
        bottom_splitter.addWidget(self.bottom_left_widget)
        bottom_splitter.addWidget(self.bottom_right_widget)
        bottom_splitter.setStretchFactor(0, 3)
        bottom_splitter.setStretchFactor(1, 1)
        bottom_layout.addWidget(bottom_splitter)
        
        self.main_splitter.addWidget(top_widget)
        self.main_splitter.addWidget(bottom_widget)
        self.main_splitter.setStretchFactor(0, 2)
        self.main_splitter.setStretchFactor(1, 5)
        
        tagging_layout.addWidget(self.main_splitter)
        
        # --- Tab 2: Analysis Results (Implication Matrix) ---
        self.tab_analysis = QWidget()
        analysis_main_layout = QVBoxLayout(self.tab_analysis)
        analysis_main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        
        lbl_hint = QLabel("<b>共現分析與蘊含矩陣 (Implication Matrix)</b>")
        lbl_hint.setStyleSheet("font-size: 14pt; margin-bottom: 20px; color: white;")
        analysis_main_layout.addWidget(lbl_hint)
        
        self.btn_export_matrix = QPushButton("輸出蘊含矩陣 (.csv)")
        self.btn_export_matrix.setFixedSize(300, 60)
        self.btn_export_matrix.setStyleSheet("background-color: #2c3e50; font-weight: bold; font-size: 12pt; color: white; border-radius: 8px;")
        self.btn_export_matrix.clicked.connect(self._on_export_matrix)
        analysis_main_layout.addWidget(self.btn_export_matrix)
        
        analysis_main_layout.addStretch()
        
        self.tabs.addTab(self.tab_tagging, "1. 分類標記管理")
        self.tabs.addTab(self.tab_analysis, "2. 關聯分析分析")
        
        main_layout.addWidget(self.tabs)

    def _create_category_row(self, cat_id: str, title: str) -> QWidget:
        bg_color = self.COLORS[cat_id]['bg']
        fg_color = self.COLORS[cat_id]['fg']
        
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        
        btn_label = QPushButton(f"{cat_id} ({title}):")
        btn_label.setToolTip(f"點擊此標籤，將下方所選單詞的分類取消")
        btn_label.setStyleSheet(f"""
            QPushButton {{
                font-size: 12pt; font-weight: bold; color: {fg_color}; 
                background-color: {bg_color}; border: 1px solid {fg_color};
                border-radius: 5px; min-width: 150px; min-height: 30px;
            }}
            QPushButton:hover {{ background-color: {fg_color}; color: #1e1e1e; }}
        """)
        btn_label.clicked.connect(self._on_unassign_category)
        
        txt_input = QLineEdit()
        txt_input.setPlaceholderText(f"新增...")
        txt_input.setStyleSheet(f"font-size: 12pt; padding: 2px; max-width: 150px; background-color: #3d3d3d; color: white; border: 1px solid {fg_color};")
        
        btn_add = QPushButton("新增標籤")
        btn_add.setStyleSheet(f"background-color: {bg_color}; color: {fg_color}; font-weight: bold; padding: 4px 10px; font-size: 10pt;")
        
        row_layout.addWidget(btn_label)
        row_layout.addWidget(txt_input)
        row_layout.addWidget(btn_add)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFixedHeight(60)
        scroll_area.setStyleSheet("background-color: #1e1e1e; border: 1px solid #3d3d3d;")
        
        tags_container = QWidget()
        tags_layout = QHBoxLayout(tags_container)
        tags_layout.setContentsMargins(2, 0, 2, 0)
        tags_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        tags_layout.setSpacing(10)
        
        # 將引用存入字典而非使用動態屬性
        self.acv_ui_refs[cat_id] = {
            'layout': tags_layout,
            'container': tags_container,
            'input': txt_input
        }
        
        # 使用預設參數擷取 cat_id
        btn_add.clicked.connect(lambda _, c=cat_id: self._on_add_category_label(c))
        txt_input.returnPressed.connect(lambda c=cat_id: self._on_add_category_label(c))
        
        scroll_area.setWidget(tags_container)
        row_layout.addWidget(scroll_area, stretch=1)
        
        return row_widget

    def _create_tag_widget(self, raw_label: str, cat_id: str) -> QFrame:
        bg_color = self.COLORS[cat_id]['bg']
        fg_color = self.COLORS[cat_id]['fg']
        
        frame = QFrame()
        frame.setStyleSheet(f"QFrame {{ background-color: {bg_color}; border: 1px solid {fg_color}; border-radius: 10px; }}")
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(2)
        
        # A0-nbn -> nbn
        display_name = raw_label.split('-', 1)[1] if '-' in raw_label else raw_label
        btn_label = QPushButton(f"{display_name}")
        btn_label.setStyleSheet(f"color: {fg_color}; font-size: 11pt; font-weight: bold; border: none; background: transparent;")
        btn_label.setToolTip(f"點擊此標籤，將下方表格中選取的單詞歸類為此標籤")
        btn_label.clicked.connect(lambda: self._on_tag_clicked(raw_label))
        layout.addWidget(btn_label)
        
        btn_delete = QPushButton("×")
        btn_delete.setFixedSize(20, 20)
        btn_delete.setStyleSheet(f"color: {fg_color}; background-color: transparent; border: none; font-weight: bold; font-size: 12pt;")
        btn_delete.clicked.connect(lambda: self._on_remove_category_label(raw_label))
        layout.addWidget(btn_delete)
        
        return frame

    def _on_add_category_label(self, cat_id: str):
        refs = self.acv_ui_refs.get(cat_id)
        if not refs: return
        
        txt_input = refs['input']
        label_text = txt_input.text().strip()
        print(f"DEBUG: _on_add_category_label called for {cat_id} with text: '{label_text}'")
        if not label_text: return
        
        new_label = self.pm.addACVLabel(cat_id, label_text)
        print(f"DEBUG: Label added to PM: {new_label}")
        
        txt_input.clear()
        import sys
        print(f"DEBUG: Text cleared, starting refresh...", flush=True)
        sys.stdout.flush()
        try:
            self._refresh_category_rows()
        except Exception as e:
            print(f"CRITICAL ERROR in _refresh_category_rows: {e}", flush=True)
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "刷新錯誤", f"在刷新時發生錯誤: {str(e)}")
        
    def _on_remove_category_label(self, raw_label: str):
        reply = QMessageBox.question(self, "刪除標籤", f"是否確定要刪除標籤「{raw_label}」？", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No: return
        self.pm.removeACVLabel(raw_label)
        self._refresh_category_rows()
        self._update_word_table()

    def _on_tag_clicked(self, raw_label: str):
        selected_items = self.word_table.selectedItems()
        if not selected_items:
            row = self.word_table.currentRow()
            if row < 0:
                QMessageBox.warning(self, "未選擇單詞", "請先在下方表格中選擇一個單詞。")
                return
        else:
            row = selected_items[0].row()
            
        item = self.word_table.item(row, 0)
        if item is None: return
        word = item.text()
        
        try:
            self.pm.assignACVLabel2word(word, raw_label)
            cat_id = raw_label[0]
            fg_color = self.COLORS[cat_id]['fg']
            
            cat_item = self.word_table.item(row, 1)
            if cat_item is not None:
                # 只在 UI 顯示名稱部分，例如 A0-nbn -> nbn
                display_name = raw_label.split('-', 1)[1] if '-' in raw_label else raw_label
                cat_item.setText(display_name)
                cat_item.setForeground(QColor(fg_color))
                # 將完整的 ID 存入自定義角色 (UserRole)，方便後續邏輯存取
                cat_item.setData(Qt.ItemDataRole.UserRole, raw_label)
        except AssertionError as e:
            QMessageBox.critical(self, "錯誤", str(e))

    def _on_unassign_category(self):
        selected_items = self.word_table.selectedItems()
        if not selected_items: return
            
        row = selected_items[0].row()
        item = self.word_table.item(row, 0)
        if item is None: return
        word = item.text()
        
        if word in self.pm.word2acvlabel:
            self.pm.word2acvlabel[word] = None
            cat_item = self.word_table.item(row, 1)
            if cat_item is not None:
                cat_item.setText("")
                cat_item.setForeground(Qt.GlobalColor.white)

    def _on_load_token_scheme(self):
        selected = self.token_scheme_list.currentItem()
        if not selected:
            QMessageBox.warning(self, "未選擇方案", "請在右下角列表選擇一個分詞方案。")
            return
            
        scheme_name = selected.text()
        
        if self.word_table.rowCount() > 0:
            reply = QMessageBox.question(
                self, "重新載入確認", 
                f"載入方案 '{scheme_name}' 將重新統計單詞，您先前的分類若已對應會保留，是否繼續？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        try:
            self.pm.loadTokenScheme2ACV(scheme_name)
            self._update_word_table()
            QMessageBox.information(self, "完成", f"已成功載入方案 '{scheme_name}'，並產生單詞表。")
        except Exception as e:
            QMessageBox.critical(self, "載入失敗", str(e))

    def _update_word_table(self):
        self.word_table.setRowCount(0)
        for word, label in self.pm.word2acvlabel.items():
            row_idx = self.word_table.rowCount()
            self.word_table.insertRow(row_idx)
            
            item_word = QTableWidgetItem(str(word))
            item_word.setFlags(item_word.flags() ^ Qt.ItemFlag.ItemIsEditable)
            
            display_text = label if label else ""
            item_cat = QTableWidgetItem(display_text)
            item_cat.setFlags(item_cat.flags() ^ Qt.ItemFlag.ItemIsEditable)
            
            if display_text:
                cat_id = display_text[0]
                fg_color = self.COLORS.get(cat_id, {}).get('fg', '#ffffff')
                
                # 同樣處理表格刷新時的顯示
                clean_name = display_text.split('-', 1)[1] if '-' in display_text else display_text
                item_cat.setText(clean_name)
                item_cat.setForeground(QColor(fg_color))
                item_cat.setData(Qt.ItemDataRole.UserRole, display_text)
            
            self.word_table.setItem(row_idx, 0, item_word)
            self.word_table.setItem(row_idx, 1, item_cat)

    def _refresh_category_rows(self):
        #print("DEBUG: Executing _refresh_category_rows...", flush=True)

        for cat_id in ['A', 'C', 'V']:
            refs = self.acv_ui_refs.get(cat_id)
            # if not refs:
            #     print(f"DEBUG: Skipping {cat_id} because refs not found", flush=True)
            #     continue
                
            layout = refs['layout']
            container = refs['container']
            
            #print(f"DEBUG: Clearing layout for {cat_id}", flush=True)
            for i in reversed(range(layout.count())):
                item = layout.takeAt(i)
                if item.widget():
                    item.widget().deleteLater()
            
            try:
                # 測試屬性存取  
                ad = self.pm.acv_dict
                #print(f"DEBUG: PM.acv_dict type: {type(ad)}", flush=True)
                
                labels = ad[cat_id]['labels']
                #print(f"DEBUG: Refreshing {cat_id}, labels count: {len(labels)}", flush=True)
                
                for raw_label in labels:
                    tag_widget = self._create_tag_widget(raw_label, cat_id)
                    layout.addWidget(tag_widget)
                    tag_widget.show()
                
                layout.addStretch()
                container.adjustSize()
                #print(f"DEBUG: {cat_id} refresh done.", flush=True)
            except Exception as e:
                #print(f"DEBUG: Error inside _refresh_category_rows for {cat_id}: {e}", flush=True)
                raise e

    def _refresh_token_scheme_list(self):
        self.token_scheme_list.clear()
        self.token_scheme_list.addItems(self.pm.token_schemes.keys())

    def _on_export_matrix(self):
        try:
            matrix_df = self.pm.genACVMatrix()
            if matrix_df.empty:
                QMessageBox.warning(self, "警告", "無法產出矩陣，請確認您已經載入分詞方案並且有標記分類過單詞。")
                return
                
            file_path, _ = QFileDialog.getSaveFileName(
                self, "儲存蘊含矩陣", "", "CSV Files (*.csv)"
            )
            
            if file_path:
                if not file_path.endswith('.csv'): file_path += '.csv'
                matrix_df.to_csv(file_path, encoding='utf-8-sig')
                QMessageBox.information(self, "成功", f"蘊含矩陣已成功匯出至：\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"匯出失敗：{str(e)}")

    def refresh_view(self):
        self._refresh_category_rows()
        self._refresh_token_scheme_list()
        self._update_word_table()
