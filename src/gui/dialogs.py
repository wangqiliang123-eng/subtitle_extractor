from PyQt5.QtWidgets import QMessageBox

def show_error(parent, message):
    """显示错误对话框"""
    QMessageBox.critical(parent, "错误", message)

def show_warning(parent, message):
    """显示警告对话框"""
    QMessageBox.warning(parent, "警告", message)

def show_info(parent, message):
    """显示信息对话框"""
    QMessageBox.information(parent, "信息", message)

def show_confirm(parent, message):
    """显示确认对话框"""
    reply = QMessageBox.question(
        parent, 
        '确认', 
        message,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    )
    return reply == QMessageBox.Yes
