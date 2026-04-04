import sys
from multiprocessing import freeze_support

if __name__ == "__main__":
    freeze_support()
    
    import os
    import platform
    from PyQt6.QtWidgets import QApplication
    from src.app import MainWindow

    # Set environment variables to prevent WebEngine crashes on some Linux configs
    if platform.system() == "Linux":
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox"
        os.environ["QT_QPA_PLATFORM"] = "xcb"

    # Put src in python path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = app.font()
    font.setPointSize(12)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())
