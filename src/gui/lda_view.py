import os
import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QLineEdit, QComboBox, QFormLayout, QGroupBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from src.core.project_manager import ProjectManager

class LDAView(QWidget):
    def __init__(self, pm: ProjectManager):
        super().__init__()
        self.pm = pm
        self.init_ui()
        self.refresh_view()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- Global Style for LDA View ---
        self.setStyleSheet("""
            QWidget {
                color: #333333;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 12pt;
                border: 1px solid #c0c0c0;
                border-radius: 6px;
                margin-top: 12px;
                background-color: #fdfdfd;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 5px;
                color: #1e3a5f;
            }
            QLabel {
                color: #000000;
            }
            QLineEdit, QComboBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #b0b0b0;
                border-radius: 4px;
                padding: 5px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #1e90ff;
            }
            QPushButton {
                color: #000000;
                background-color: #e4e4e4;
                border: 1px solid #b0b0b0;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QCheckBox {
                spacing: 8px;
                color: #2c3e50;
                font-weight: bold;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:unchecked:hover {
                border-color: #3498db;
            }
            QCheckBox::indicator:checked {
                background-color: #1e3a5f;
                border-color: #1e3a5f;
                /* Note: Standard indicator image will depend on OS/Theme unless defined */
            }
            QCheckBox::indicator:checked:hover {
                background-color: #2c3e50;
                border-color: #2c3e50;
            }
        """)

        # --- Top Section: Token Scheme and Synonyms ---
        top_group = QGroupBox("1. 資料準備")
        top_layout = QVBoxLayout()
        
        # Token scheme 
        scheme_layout = QHBoxLayout()
        scheme_layout.addWidget(QLabel("選擇分詞方案:"))
        self.cb_token_scheme = QComboBox()
        scheme_layout.addWidget(self.cb_token_scheme, stretch=1)
        self.btn_load_scheme = QPushButton("載入分詞方案")
        self.btn_load_scheme.clicked.connect(self._on_load_scheme)
        scheme_layout.addWidget(self.btn_load_scheme)
        top_layout.addLayout(scheme_layout)
        
        # Synonyms
        synonym_layout = QHBoxLayout()
        self.btn_load_synonyms = QPushButton("載入同義詞")
        self.btn_load_synonyms.clicked.connect(self._on_load_synonyms)
        synonym_layout.addWidget(self.btn_load_synonyms)
        self.lbl_synonym_path = QLabel("尚未載入同義詞")
        self.lbl_synonym_path.setStyleSheet("color: gray;")
        synonym_layout.addWidget(self.lbl_synonym_path, stretch=1)
        top_layout.addLayout(synonym_layout)
        
        top_group.setLayout(top_layout)
        main_layout.addWidget(top_group)
        
        # --- Middle Section: Parameters ---
        param_group = QGroupBox("2. LDA 參數設置")
        param_layout = QHBoxLayout()
        
        from PyQt6.QtWidgets import QCheckBox
        form_left = QFormLayout()
        
        self.chk_tfidf = QCheckBox("使用 TF-IDF 過濾模式")
        self.chk_tfidf.setChecked(True)
        form_left.addRow("", self.chk_tfidf)
        
        self.le_alpha = QLineEdit("auto")
        self.le_beta = QLineEdit("auto")
        self.le_low_freq = QLineEdit("2")  
        self.le_high_freq = QLineEdit("0.4") 
        form_left.addRow("Alpha:", self.le_alpha)
        form_left.addRow("Beta:", self.le_beta)
        form_left.addRow("低頻過濾 (n_min):", self.le_low_freq)
        form_left.addRow("高頻過濾 (n_max):", self.le_high_freq)
        
        form_right = QFormLayout()
        self.le_iter = QLineEdit("50")
        self.le_n_min = QLineEdit("2")
        self.le_n_max = QLineEdit("20")
        self.le_n_final = QLineEdit("5")
        form_right.addRow("Iterations:", self.le_iter)
        form_right.addRow("Sweep 主題數下限:", self.le_n_min)
        form_right.addRow("Sweep 主題數上限:", self.le_n_max)
        form_right.addRow("Final 主題數:", self.le_n_final)
        
        param_layout.addLayout(form_left)
        param_layout.addLayout(form_right)
        param_group.setLayout(param_layout)
        main_layout.addWidget(param_group)
        
        # --- Sweep Plot Area ---
        self.plot_group = QGroupBox("Sweep 評估結果 (Perplexity & Coherence)")
        plot_layout = QVBoxLayout()
        self.lbl_eval_result = QLabel("Sweep 尚未執行。\n這裡將會顯示 Perplexity 與 Coherence 的評估結果及圖表。")
        self.lbl_eval_result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_eval_result.setMinimumHeight(200)
        self.lbl_eval_result.setStyleSheet("background-color: #f8f9fa; color: #333333; border: 1px solid #dee2e6; border-radius: 4px; font-size: 14pt;")
        plot_layout.addWidget(self.lbl_eval_result)
        self.plot_group.setLayout(plot_layout)
        main_layout.addWidget(self.plot_group, stretch=1)
        
        # --- Bottom Section: Action Buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_layout.setSpacing(30)
        
        btn_style = "background-color: #2e7d32; font-weight: bold; font-size: 14pt; color: white; border-radius: 8px; padding: 10px;"
        
        self.btn_sweep = QPushButton("Sweep (主題數尋優)")
        self.btn_sweep.setFixedSize(250, 60)
        self.btn_sweep.setStyleSheet(btn_style)
        self.btn_sweep.clicked.connect(self._on_sweep)
        btn_layout.addWidget(self.btn_sweep)
        
        self.btn_final = QPushButton("Final (計算與輸出)")
        self.btn_final.setFixedSize(250, 60)
        self.btn_final.setStyleSheet(btn_style)
        self.btn_final.clicked.connect(self._on_final_analysis)
        btn_layout.addWidget(self.btn_final)
        
        main_layout.addLayout(btn_layout)

    def refresh_view(self):
        # 暫時阻斷訊號，防止 clear() 觸發下拉選單的變動事件
        self.cb_token_scheme.blockSignals(True)
        current_text = self.cb_token_scheme.currentText()
        self.cb_token_scheme.clear()
        
        schemes = list(self.pm.token_schemes.keys())
        self.cb_token_scheme.addItems(schemes)
        
        if current_text in schemes:
            self.cb_token_scheme.setCurrentText(current_text)
        elif schemes:
            self.cb_token_scheme.setCurrentIndex(0)
            
        self.cb_token_scheme.blockSignals(False)
        
        # 恢復最後一次的 Sweep 結果
        self._update_sweep_label(self.pm.last_lda_sweep)
        
    def _update_sweep_label(self, results):
        if not results:
            return
            
        res_str = f"最後一次 Sweep 評估結果：\n"
        for i, r in enumerate(results, start=1):
            if i % 2 == 1:
                res_str += f"K={r['k']}   |   Perplexity: {r['perplexity']:.3f}   |   Coherence: {r['coherence']:.4f}  "
            else:
                res_str += f"K={r['k']}   |   Perplexity: {r['perplexity']:.3f}   |   Coherence: {r['coherence']:.4f}\n"
        self.lbl_eval_result.setText(res_str)
        self.lbl_eval_result.setStyleSheet("background-color: #f0f8ff; color: #1e3a5f; border: 1px solid #1e90ff; border-radius: 4px; font-size: 14pt; padding: 10px;")
        
    def _on_load_scheme(self):
        scheme_name = self.cb_token_scheme.currentText()
        if not scheme_name:
            QMessageBox.warning(self, "警告", "請先選擇一個分詞方案！")
            return
        try:
            self.pm.loadTokenScheme2LDA(scheme_name)
            QMessageBox.information(self, "成功", f"成功載入分詞方案：{scheme_name}")
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"載入分詞方案失敗：{e}")

    def _on_load_synonyms(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "選擇同義詞文本", "", "Text Files (*.txt)")
        if filepath:
            try:
                self.pm.loadSynonyms2LDA(filepath)
                self.lbl_synonym_path.setText(filepath)
                self.lbl_synonym_path.setStyleSheet("color: black;")
                QMessageBox.information(self, "成功", "同義詞載入成功！")
            except Exception as e:
                QMessageBox.critical(self, "錯誤", f"同義詞載入失敗：{e}")
                
    def _get_params(self):
        # 輔助函數：從 UI 取得所有參數
        return {
            'alpha': self.le_alpha.text().strip(),
            'beta': self.le_beta.text().strip(),
            'low_freq': self.le_low_freq.text().strip(),
            'high_freq': self.le_high_freq.text().strip(),
            'iterations': int(self.le_iter.text().strip() or 50),
            'n_min': int(self.le_n_min.text().strip() or 2),
            'n_max': int(self.le_n_max.text().strip() or 20),
            'n_final': int(self.le_n_final.text().strip() or 5),
            'use_tfidf': self.chk_tfidf.isChecked()
        }

    def _on_sweep(self):
        try:
            params = self._get_params()
            
            project_path = self.pm.getProjectPath
            if not project_path:
                QMessageBox.warning(self, "警告", "請先儲存專案以決定輸出路徑！")
                return
                
            project_name = os.path.basename(project_path).replace(".aproj", "")
            base_dir = os.path.dirname(project_path)
            
            self.lbl_eval_result.setText("Sweep 執行中... 排程較久，請留意背景視窗並請稍候...")
            
            # 使用 Process Events 刷新 UI 防止卡住
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            
            results = self.pm.genLDASweep(params, base_dir, f"{project_name}-{self.cb_token_scheme.currentText()}")
            
            # 使用統一的方法來更新介面
            self._update_sweep_label(results)
            
            QMessageBox.information(self, "成功", "Sweep 計算完成！請根據文字面板的數值決定 Final 主題數。")

            
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"Sweep 失敗：{e}")

    def _on_final_analysis(self):
        scheme_name = self.cb_token_scheme.currentText()
        if not scheme_name:
            QMessageBox.warning(self, "警告", "請先載入分詞方案！")
            return
            
        try:
            params = self._get_params()
            project_path = self.pm.getProjectPath
            if not project_path:
                QMessageBox.warning(self, "警告", "請先儲存專案以決定輸出路徑！")
                return
                
            project_name = os.path.basename(project_path).replace(".aproj", "")
            base_dir = os.path.dirname(project_path)
            prefix = f"{project_name}-{scheme_name}"
            
            # 使用 Process Events 刷新 UI
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            
            res = self.pm.genLDAFinal(params, base_dir, prefix)
            
            filesToCreate = [
                f"{prefix}-K{res['k']}-ldavis.html",
                f"{prefix}-K{res['k']}-relation.html",
                #f"{prefix}-K{res['k']}-network.html",
                f"{prefix}-K{res['k']}-heatmap.png",
                f"{prefix}-K{res['k']}-word_distribution.csv",
                f"{prefix}-K{res['k']}-topics.csv"
            ]
            
            QMessageBox.information(self, "成功", f"Final 分析已完成，並在專案目錄下產生了以下輸出：\n\n" + "\n".join(filesToCreate))
        except Exception as e:
            QMessageBox.critical(self, "錯誤", f"Final 分析失敗：{e}")
