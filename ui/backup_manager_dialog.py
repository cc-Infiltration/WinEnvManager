from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem,
    QSplitter, QMessageBox, QInputDialog
)
from PyQt5.QtCore import Qt

class BackupManagerDialog(QDialog):
    """备份管理对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("备份管理")
        self.setMinimumSize(800, 600)
        
        # 导入BackupManager
        from modules.backup_manager import BackupManager
        self.backup_manager = BackupManager()
        
        # 创建布局
        layout = QVBoxLayout(self)
        
        # 顶部按钮
        button_layout = QHBoxLayout()
        self.refresh_button = QPushButton("刷新")
        self.new_backup_button = QPushButton("新建备份")
        self.restore_button = QPushButton("恢复")
        self.delete_button = QPushButton("删除")
        
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.new_backup_button)
        button_layout.addWidget(self.restore_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # 分割器
        splitter = QSplitter(Qt.Vertical)
        
        # 备份列表
        self.backup_tree = QTreeWidget()
        self.backup_tree.setHeaderLabels(["文件名", "时间", "描述", "系统变量数", "用户变量数"])
        self.backup_tree.setSelectionMode(QTreeWidget.SingleSelection)
        
        # 备份详情
        self.detail_tree = QTreeWidget()
        self.detail_tree.setHeaderLabels(["变量类型", "变量名", "值"])
        
        splitter.addWidget(self.backup_tree)
        splitter.addWidget(self.detail_tree)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
        
        # 连接信号
        self.refresh_button.clicked.connect(self.load_backups)
        self.new_backup_button.clicked.connect(self.create_new_backup)
        self.restore_button.clicked.connect(self.restore_backup)
        self.delete_button.clicked.connect(self.delete_backup)
        self.backup_tree.itemSelectionChanged.connect(self.show_backup_details)
        
        # 加载备份列表
        self.load_backups()
    
    def load_backups(self):
        """加载备份列表"""
        self.backup_tree.clear()
        backups = self.backup_manager.get_backup_list()
        
        for backup in backups:
            item = QTreeWidgetItem([
                backup["filename"],
                backup["timestamp"],
                backup["description"],
                str(backup["system_count"]),
                str(backup["user_count"])
            ])
            item.setData(0, Qt.UserRole, backup["path"])
            self.backup_tree.addTopLevelItem(item)
        
        # 自动展开第一个项目
        if self.backup_tree.topLevelItemCount() > 0:
            self.backup_tree.setCurrentItem(self.backup_tree.topLevelItem(0))
    
    def create_new_backup(self):
        """创建新备份"""
        description, ok = QInputDialog.getText(self, "新建备份", "请输入备份描述:")
        if ok:
            success, message = self.backup_manager.create_backup(description)
            if success:
                QMessageBox.information(self, "成功", "备份创建成功")
                self.load_backups()
            else:
                QMessageBox.warning(self, "失败", f"备份创建失败: {message}")
    
    def show_backup_details(self):
        """显示备份详情"""
        self.detail_tree.clear()
        
        selected_item = self.backup_tree.currentItem()
        if not selected_item:
            return
        
        backup_path = selected_item.data(0, Qt.UserRole)
        backup_data = self.backup_manager.get_backup_details(backup_path)
        
        if backup_data:
            # 添加系统变量
            system_vars = backup_data.get("system_variables", {})
            for name, value in system_vars.items():
                QTreeWidgetItem(self.detail_tree, ["System", name, value])
            
            # 添加用户变量
            user_vars = backup_data.get("user_variables", {})
            for name, value in user_vars.items():
                QTreeWidgetItem(self.detail_tree, ["User", name, value])
    
    def restore_backup(self):
        """恢复备份"""
        selected_item = self.backup_tree.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "警告", "请选择要恢复的备份")
            return
        
        backup_path = selected_item.data(0, Qt.UserRole)
        
        # 确认恢复
        reply = QMessageBox.question(
            self, "确认恢复", "恢复备份将覆盖当前环境变量设置，是否继续?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            success, invalid_vars = self.backup_manager.restore_backup(backup_path)
            if success:
                if invalid_vars:
                    QMessageBox.warning(
                        self, "部分恢复成功",
                        f"恢复成功，但以下变量无法恢复:\n{chr(10).join(invalid_vars)}"
                    )
                else:
                    QMessageBox.information(self, "成功", "备份恢复成功")
                # 刷新主界面
                if hasattr(self.parent(), 'load_variables'):
                    self.parent().load_variables()
                self.accept()
            else:
                QMessageBox.critical(self, "失败", f"恢复备份失败: {invalid_vars[0]}")
    
    def delete_backup(self):
        """删除备份"""
        selected_item = self.backup_tree.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "警告", "请选择要删除的备份")
            return
        
        backup_path = selected_item.data(0, Qt.UserRole)
        filename = selected_item.text(0)
        
        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除备份 '{filename}' 吗?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.backup_manager.delete_backup(backup_path):
                QMessageBox.information(self, "成功", "备份删除成功")
                self.load_backups()
            else:
                QMessageBox.warning(self, "失败", "备份删除失败")