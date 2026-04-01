import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QMessageBox, QStackedWidget
)
from PyQt6.QtCore import Qt
from .core.project_manager import ProjectManager
from .gui.tokenization_view import TokenizationView
from .gui.acv_view import ACVView
from .gui.lda_view import LDAView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ACV 分析系統 (New Architecture)")
        self.resize(1920, 800) 

        self.pm = ProjectManager()

        self.init_ui()
        self.update_ui_state()

    def init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        central_widget.setStyleSheet("QWidget#CentralWidget { background-color: #ffffff; }")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Top Toolbar ---
        toolbar_container = QWidget()
        #toolbar_container.setStyleSheet("background-color: #f0f0f0; border-bottom: 1px solid #c0c0c0;")
        toolbar_container.setStyleSheet("""
            #ToolbarContainer {
                background-color: #f0f0f0; 
                border-bottom: 1px solid #c0c0c0;
            }
            QPushButton {
                color: black;
                background-color: #e4e4e4;
                border: 1px solid #b0b0b0;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QPushButton:disabled {
                color: #a0a0a0;
            }
        """)
        toolbar_layout = QHBoxLayout(toolbar_container)
        toolbar_layout.setContentsMargins(10, 5, 10, 5)

        self.btn_new = QPushButton("新建專案 (New)")
        self.btn_new.clicked.connect(self.action_new_project)
        toolbar_layout.addWidget(self.btn_new)

        self.btn_open = QPushButton("開啟專案 (Open)")
        self.btn_open.clicked.connect(self.action_open_project)
        toolbar_layout.addWidget(self.btn_open)

        self.btn_save = QPushButton("儲存專案 (Save)")
        self.btn_save.clicked.connect(self.action_save_project)
        toolbar_layout.addWidget(self.btn_save)

        self.lbl_project_status = QLabel("未載入專案")
        self.lbl_project_status.setStyleSheet("color: gray;")
        self.lbl_project_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        toolbar_layout.addWidget(self.lbl_project_status, stretch=1)

        main_layout.addWidget(toolbar_container)

        # --- Body ---
        body_container = QWidget()
        body_layout = QHBoxLayout(body_container)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Sidebar
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(220)
        self.sidebar.setStyleSheet("background-color: #f5f5f5; border-right: 1px solid #c0c0c0;")
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        nav_btn_style = """
            QPushButton {
                background-color: transparent;
                color: #333333;
                text-align: left;
                padding: 15px 20px;
                border: none;
                border-left: 5px solid transparent;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
            QPushButton:disabled {
                color: #a0a0a0;
            }
            QPushButton:checked {
                background-color: #ffffff;
                color: #000000;
                font-weight: bold;
                border-top: 1px solid #c0c0c0;
                border-bottom: 1px solid #c0c0c0;
                border-left: 5px solid #1e90ff;
                margin-right: -1px;  /* Covers the sidebar's right border to connect with main content */
            }
        """
        self.btn_nav_tokenize = QPushButton("1. 建立分詞表")
        self.btn_nav_tokenize.setStyleSheet(nav_btn_style)
        self.btn_nav_tokenize.setCheckable(True)
        self.btn_nav_tokenize.clicked.connect(lambda: self.switch_view(0))
        sidebar_layout.addWidget(self.btn_nav_tokenize)

        self.btn_nav_acv = QPushButton("2. ACV 分析")
        self.btn_nav_acv.setStyleSheet(nav_btn_style)
        self.btn_nav_acv.setCheckable(True)
        self.btn_nav_acv.clicked.connect(lambda: self.switch_view(1)) 
        sidebar_layout.addWidget(self.btn_nav_acv)

        self.btn_nav_lda = QPushButton("3. LDA 分析")
        self.btn_nav_lda.setStyleSheet(nav_btn_style)
        self.btn_nav_lda.setCheckable(True)
        self.btn_nav_lda.clicked.connect(lambda: self.switch_view(2)) 
        sidebar_layout.addWidget(self.btn_nav_lda)
        
        body_layout.addWidget(self.sidebar)

        # Content
        self.content_stack = QStackedWidget()
        self.tokenize_view = TokenizationView(self.pm, self.refresh_all_views)
        self.content_stack.addWidget(self.tokenize_view) 
        
        self.acv_view = ACVView(self.pm)
        self.content_stack.addWidget(self.acv_view) 

        self.lda_view = LDAView(self.pm)
        self.content_stack.addWidget(self.lda_view)
        
        body_layout.addWidget(self.content_stack, stretch=1)
        main_layout.addWidget(body_container, stretch=1)

    def update_ui_state(self):
        has_data = len(self.pm.raw_data) > 0
        self.btn_save.setEnabled(has_data)
        
        # 斷詞頁面應該永遠保持開啟，因為它是資料載入的入口
        self.btn_nav_tokenize.setEnabled(True)
        # 分析頁面則需要有資料才能進入
        self.btn_nav_acv.setEnabled(has_data)
        self.btn_nav_lda.setEnabled(has_data)
        
        filename = os.path.basename(self.pm.getProjectPath) if self.pm.getProjectPath else "未儲存"
        self.lbl_project_status.setText(f"當前專案: {filename}")

    def switch_view(self, index):
        self.content_stack.setCurrentIndex(index)
        self.btn_nav_tokenize.setChecked(index == 0)
        self.btn_nav_acv.setChecked(index == 1)
        self.btn_nav_lda.setChecked(index == 2)

    def refresh_all_views(self):
        """Called when significant global state changes (like new project loaded)."""
        self.update_ui_state()
        self.tokenize_view.refresh_view()
        self.acv_view.refresh_view()
        self.lda_view.refresh_view()

    def action_new_project(self):
        if len(self.pm.raw_data) > 0:
            reply = QMessageBox.question(self, "警告", "這會重置目前數據，確定繼續？", 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No: return
        
        filepath, _ = QFileDialog.getSaveFileName(self, "建立新專案", "", "ACV Project Files (*.aproj)")
        if filepath:
            # 自動補足副檔名
            if not filepath.lower().endswith('.aproj'):
                filepath += '.aproj'
                
            self.pm = ProjectManager() 
            self.pm.createProject(filepath) # Set initial path
            self.tokenize_view.pm = self.pm
            self.pm.saveProject()
            self.update_ui_state()
            self.switch_view(0)

    def action_open_project(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "開啟專案", "", "ACV Project Files (*.aproj)")
        if filepath:
            try:
                self.pm.loadProject(filepath)
                self.tokenize_view.pm = self.pm
                self.update_ui_state()
                self.refresh_all_views()
                QMessageBox.information(self, "成功", "專案載入成功！")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"載入失敗: {e}")

    def action_save_project(self):
        filepath = self.pm.getProjectPath
        if not filepath:
            self.action_new_project()
            return
            
        # 儲存時再次檢查副檔名 (如果是從 ProjectManager 拿到的舊路徑可能沒副檔名)
        if not filepath.lower().endswith('.aproj'):
            filepath += '.aproj'

        try:
            self.pm.saveProject()
            QMessageBox.information(self, "成功", "專案儲存成功！")
            self.update_ui_state()
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"儲存失敗: {e}")
