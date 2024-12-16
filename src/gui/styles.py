# 按钮样式
BUTTON_STYLE = """
    QPushButton {
        padding: 8px 16px;
        background-color: #4a90e2;
        color: white;
        border: none;
        border-radius: 4px;
        min-width: 80px;
    }
    QPushButton:hover {
        background-color: #357abd;
    }
    QPushButton:pressed {
        background-color: #2a5f9e;
    }
    QPushButton:disabled {
        background-color: #cccccc;
    }
"""

# 列表样式
LIST_STYLE = """
    QListWidget {
        border: 1px solid #ccc;
        border-radius: 4px;
        padding: 5px;
        background-color: white;
    }
    QListWidget::item {
        padding: 5px;
        border-bottom: 1px solid #eee;
    }
    QListWidget::item:selected {
        background-color: #e6f3ff;
        color: black;
    }
"""

# 文本编辑器样式
TEXT_EDIT_STYLE = """
    QTextEdit {
        border: 1px solid #ccc;
        border-radius: 4px;
        padding: 5px;
        background-color: white;
        font-family: Consolas, Monaco, monospace;
    }
"""

# 标签样式
LABEL_STYLE = """
    QLabel {
        font-weight: bold;
        margin-top: 10px;
    }
"""