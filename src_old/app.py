import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QMessageBox, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from .core.project_manager import ProjectManager
from .gui.tokenization_view import TokenizationView
from .gui.acv_view import ACVView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ACV 分析系統")
        self.resize(1920, 1080) # 4K default size

        self.pm = ProjectManager()
        self.current_project_file = None

        self.init_ui()
        self.update_ui_state()

    def init_ui(self):
        # Central widget and main layout
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        central_widget.setStyleSheet("QWidget#CentralWidget { background-color: #ffffff; }")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Top Toolbar ---
        toolbar_container = QWidget()
        toolbar_container.setObjectName("ToolbarContainer")
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

        # --- Body Layout (Sidebar + Content) ---
        body_container = QWidget()
        body_layout = QHBoxLayout(body_container)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Left Sidebar
        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(220)
        self.sidebar.setStyleSheet("""
            QWidget#Sidebar {
                background-color: #f5f5f5;
                border-right: 1px solid #c0c0c0;
            }
        """)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 20, 0, 20)
        sidebar_layout.setSpacing(0)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Navigation Buttons style
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
        
        # Group buttons visually (but we'll manage checked state manually)
        self.nav_buttons = [self.btn_nav_tokenize, self.btn_nav_acv, self.btn_nav_lda]

        body_layout.addWidget(self.sidebar)

        # Right Content Area (QStackedWidget)
        self.content_stack = QStackedWidget()
        
        # Add views
        self.tokenize_view = TokenizationView(self.pm, self.refresh_all_views)
        self.content_stack.addWidget(self.tokenize_view) # Index 0
        
        # Add ACV View
        self.acv_view = ACVView(self.pm, parent=self)
        self.acv_view.refresh_callback = self.refresh_all_views
        self.content_stack.addWidget(self.acv_view) # Index 1
        
        lda_placeholder = QLabel("LDA 分析介面建置中...")
        lda_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_stack.addWidget(lda_placeholder) # Index 2

        body_layout.addWidget(self.content_stack, stretch=1)
        
        main_layout.addWidget(body_container, stretch=1)

    def update_ui_state(self):
        """Enable/Disable UI elements based on project presence and state."""
        has_project = self.current_project_file is not None or self.pm.raw_data is not None

        if has_project:
            self.btn_save.setEnabled(True)
            self.btn_nav_tokenize.setEnabled(True)
            filename = os.path.basename(self.current_project_file) if self.current_project_file else "未儲存"
            self.lbl_project_status.setText(f"當前專案: {filename}")
            
            # ACV and LDA are unlocked only after tokenization data exists
            if self.pm.tokenized_data is not None and not self.pm.tokenized_data.empty:
                self.btn_nav_acv.setEnabled(True)
                self.btn_nav_lda.setEnabled(True)
            else:
                self.btn_nav_acv.setEnabled(False)
                self.btn_nav_lda.setEnabled(False)
        else:
            self.btn_save.setEnabled(False)
            self.btn_nav_tokenize.setEnabled(False)
            self.btn_nav_acv.setEnabled(False)
            self.btn_nav_lda.setEnabled(False)
            self.lbl_project_status.setText("未載入專案")

    def switch_view(self, index):
        """Switch the stacked widget view."""
        self.content_stack.setCurrentIndex(index)
        
        # Update checked state for visually active tab
        for i, btn in enumerate(self.nav_buttons):
            if i == index:
                btn.setChecked(True)
            else:
                btn.setChecked(False)
                
        # Call refresh method if the widget has one
        current_widget = self.content_stack.currentWidget()
        if hasattr(current_widget, 'refresh_view'):
            current_widget.refresh_view()

    def refresh_all_views(self):
        """Force all tabs to refresh their data from the ProjectManager."""
        self.update_ui_state()
        for i in range(self.content_stack.count()):
            widget = self.content_stack.widget(i)
            if hasattr(widget, 'refresh_view'):
                widget.refresh_view()

    def action_new_project(self):
        """Create a new project workspace."""
        if self.pm.raw_data is not None:
            reply = QMessageBox.question(self, "警告", "這會清空目前的專案，確定繼續？", 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "建立新專案", "", "ACV Project Files (*.aproj);;All Files (*)"
        )
        
        if filepath:
            self.pm = ProjectManager() # Reset
            
            # Recreate views to bind new PM
            self.tokenize_view.pm = self.pm
            self.acv_view.pm = self.pm
            
            self.current_project_file = filepath
            self.pm.save_project(self.current_project_file) # Initialize file
            self.update_ui_state()
            self.switch_view(0)

    def action_open_project(self):
        """Open an existing .aproj file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "開啟專案", "", "ACV Project Files (*.aproj);;All Files (*)"
        )
        
        if filepath:
            try:
                self.pm = ProjectManager()
                self.pm.load_project(filepath)
                
                # Update views with new PM
                self.tokenize_view.pm = self.pm
                self.acv_view.pm = self.pm
                
                self.current_project_file = filepath
                self.update_ui_state()
                self.switch_view(0)
                QMessageBox.information(self, "成功", "專案載入成功！")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"載入專案失敗:\n{str(e)}")

    def action_save_project(self):
        """Save the current project state."""
        if self.current_project_file:
            try:
                self.pm.save_project(self.current_project_file)
                QMessageBox.information(self, "成功", "專案儲存成功！")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"儲存專案失敗:\n{str(e)}")
        else:
            self.action_new_project() # Redirect to 'save as' essentially
