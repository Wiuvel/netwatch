# -*- coding: utf-8 -*-
import sys
import logging
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

def setup_logging():
    logger = logging.getLogger("NetWatch")
    logger.setLevel(logging.DEBUG)
    
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    return logger

def main():
    # Initialize logging
    setup_logging()
    
    # Initialize Application
    app = QApplication(sys.argv)
    app.setApplicationName("Net Watch")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run the event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
