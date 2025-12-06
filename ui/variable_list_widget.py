from PyQt5.QtWidgets import QListWidget, QMenu, QMessageBox
from PyQt5.QtCore import Qt, QUrl, QMimeData
from PyQt5.QtGui import QDragEnterEvent, QDropEvent
import os

class VariableListWidget(QListWidget):
    """变量列表控件，支持拖拽和右键菜单"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.parent = parent
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        """拖拽释放事件"""
        urls = event.mimeData().urls()
        for url in urls:
            path = url.toLocalFile()
            if os.path.exists(path):
                # 生成变量名
                filename = os.path.basename(path)
                var_name = filename.upper().replace(' ', '_') + '_PATH'
                
                # 检查变量名是否重复
                current_vars = self.parent.env_manager.get_variables(self.parent.current_var_type)
                if var_name in current_vars:
                    # 生成唯一变量名
                    counter = 1
                    while f"{var_name}_{counter}" in current_vars:
                        counter += 1
                    var_name = f"{var_name}_{counter}"
                
                # 添加变量
                if self.parent.env_manager.add_variable(self.parent.current_var_type, var_name, path):
                    self.parent.load_variables()
                    QMessageBox.information(self, "成功", f"变量 {var_name} 添加成功")
                else:
                    QMessageBox.warning(self, "失败", f"添加变量 {var_name} 失败，请检查权限")
    
    def show_context_menu(self, position):
        """显示右键菜单"""
        menu = QMenu(self)
        
        # 添加菜单项
        add_action = menu.addAction("添加变量")
        edit_action = menu.addAction("编辑变量")
        delete_action = menu.addAction("删除变量")
        validate_action = menu.addAction("验证变量")
        menu.addSeparator()
        backup_action = menu.addAction("备份管理")
        
        # 获取当前选中项
        selected_item = self.currentItem()
        if not selected_item:
            edit_action.setEnabled(False)
            delete_action.setEnabled(False)
        
        # 连接菜单项信号
        add_action.triggered.connect(self.parent.show_add_variable_dialog)
        edit_action.triggered.connect(self.parent.show_edit_variable_dialog)
        delete_action.triggered.connect(self.parent.delete_variable)
        validate_action.triggered.connect(self.parent.validate_selected_variable)
        backup_action.triggered.connect(self.parent.show_backup_manager)
        
        # 显示菜单
        menu.exec_(self.mapToGlobal(position))