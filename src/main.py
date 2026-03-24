import sys
import os
import platform

# Set environment variables to prevent WebEngine crashes on some Linux configs
if platform.system() == "Linux":
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox"
    os.environ["QT_QPA_PLATFORM"] = "xcb"

# Put src in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from src_new.app import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = app.font()
    font.setPointSize(14)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
