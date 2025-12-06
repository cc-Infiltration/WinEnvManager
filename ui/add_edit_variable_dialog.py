from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout,
    QDialogButtonBox, QFileDialog
)

class AddEditVariableDialog(QDialog):
    """添加/编辑变量对话框"""
    def __init__(self, parent=None, var_type="user", name="", value=""):
        super().__init__(parent)
        self.setWindowTitle("添加变量" if not name else "编辑变量")
        self.var_type = var_type
        
        layout = QFormLayout(self)
        
        # 变量名输入框
        self.name_input = QLineEdit(name)
        layout.addRow(QLabel("变量名:"), self.name_input)
        
        # 变量值输入框
        self.value_input = QLineEdit(value)
        layout.addRow(QLabel("变量值:"), self.value_input)
        
        # 浏览按钮
        self.browse_button = QPushButton("浏览文件")
        self.browse_folder_button = QPushButton("浏览文件夹")
        
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.browse_button)
        button_layout.addWidget(self.browse_folder_button)
        layout.addRow(button_layout)
        
        # 按钮盒
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addRow(self.button_box)
        
        # 连接信号
        self.browse_button.clicked.connect(self.browse_file)
        self.browse_folder_button.clicked.connect(self.browse_folder)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        # 设置焦点
        self.name_input.setFocus()
    
    def browse_file(self):
        """浏览文件"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件")
        if file_path:
            self.value_input.setText(file_path)
    
    def browse_folder(self):
        """浏览文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_path:
            self.value_input.setText(folder_path)
    
    def get_data(self):
        """获取输入数据"""
        return self.name_input.text().strip(), self.value_input.text().strip()