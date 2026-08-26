import sys
import os
import json
import winreg
import threading

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QTabWidget, QListWidget,
    QListWidgetItem, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFileDialog, QMessageBox, QMenu, QInputDialog, QDialog,
    QFormLayout, QDialogButtonBox, QTreeWidget, QTreeWidgetItem,
    QSplitter, QCheckBox, QStyledItemDelegate
)
from PyQt5.QtCore import Qt, QUrl, QMimeData
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QFont, QColor, QPalette

# 创建backup目录
backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backup')
if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)

def path_exists_with_timeout(path, timeout=2.0):
    """带超时的路径存在性检查，防止不可达的网络路径长时间卡死界面"""
    result = [False]
    def _check():
        try:
            result[0] = os.path.exists(path)
        except Exception:
            result[0] = False
    t = threading.Thread(target=_check, daemon=True)
    t.start()
    t.join(timeout)
    return result[0]

def is_valid_path(path):
    """检查路径是否有效（用于标红判断）"""
    path = path.strip()
    if not path:
        return False
    # 仅盘符如 "C:" 不是有效路径，但 os.path.exists("C:") 在 Windows 下会返回 True
    if len(path) == 2 and path[1] == ':':
        return False
    expanded = os.path.expandvars(path)
    # 网络路径(UNC)的存在性检查可能因地址不可达而长时间阻塞，加超时保护
    if expanded.startswith('\\\\'):
        return path_exists_with_timeout(expanded)
    return os.path.exists(expanded)

# ===== Midnight Mist 柔和主题样式表 =====
STYLESHEET = """
* {
    font-family: "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
    outline: none;
}

QWidget {
    background-color: #1C1E22;
    color: #D8DCE3;
}

QMainWindow, QDialog {
    background-color: #1C1E22;
}

/* —— 顶部标题区 —— */
QLabel#HeaderTitle {
    font-size: 16px;
    font-weight: 600;
    color: #E4E7EC;
    letter-spacing: 0.5px;
}
QLabel#HeaderSubtitle {
    color: #8A909A;
    font-size: 11px;
    letter-spacing: 0.3px;
}
QLabel#permBadge {
    color: #8A909A;
    border: 1px solid #3A3E45;
    border-radius: 11px;
    padding: 3px 14px;
    font-size: 11px;
    font-weight: 600;
}

/* —— 标签页 —— */
QTabWidget::pane {
    border: 1px solid #2E3238;
    border-radius: 8px;
    background: #1C1E22;
    top: -1px;
}
QTabBar {
    background: transparent;
}
QTabBar::tab {
    background: transparent;
    color: #7A808A;
    padding: 9px 22px;
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 2px;
    font-weight: 500;
}
QTabBar::tab:hover { color: #B4B9C2; }
QTabBar::tab:selected {
    color: #8FA8B0;
    border-bottom: 2px solid #6A8490;
}

/* —— 列表控件 —— */
QListWidget {
    background-color: #222529;
    alternate-background-color: #25292E;
    border: 1px solid #2E3238;
    border-radius: 8px;
    padding: 4px;
    font-family: "Cascadia Mono", "Consolas", "Cascadia Code", monospace;
    font-size: 12px;
}
QListWidget::item {
    padding: 9px 10px;
    border-bottom: 1px solid #272B31;
    border-radius: 4px;
    /* 不在此处设置 color，否则会覆盖代码中 setForeground 的标红/标绿 */
}
QListWidget::item:hover { background-color: #262A30; }
QListWidget::item:selected {
    background-color: #2E3A44;
    border-left: 3px solid #7B9BA6;
}

/* —— 树控件 —— */
QTreeWidget {
    background-color: #222529;
    border: 1px solid #2E3238;
    border-radius: 8px;
    padding: 4px;
    alternate-background-color: #25292E;
}
QTreeWidget::item {
    padding: 6px 4px;
    border-bottom: 1px solid #272B31;
}
QTreeWidget::item:hover { background-color: #262A30; }
QTreeWidget::item:selected {
    background-color: #2E3A44;
    border-left: 3px solid #7B9BA6;
}
QHeaderView::section {
    background-color: #1C1E22;
    color: #7A808A;
    padding: 7px 8px;
    border: none;
    border-bottom: 1px solid #2E3238;
    border-right: 1px solid #25292E;
    font-weight: 600;
    font-size: 11px;
}
QTreeView::indicator, QCheckBox::indicator {
    width: 14px; height: 14px;
}

/* —— 单行输入框 —— */
QLineEdit {
    background-color: #222529;
    border: 1px solid #2E3238;
    border-radius: 7px;
    padding: 8px 12px;
    color: #D8DCE3;
    selection-background-color: #4A5A68;
    selection-color: #E4E7EC;
}
QLineEdit:focus { border: 1px solid #6A8490; }
QLineEdit::placeholder { color: #7A808A; }

/* —— 按钮 —— */
QPushButton {
    background-color: #2A2D32;
    color: #B4B9C2;
    border: 1px solid #363A40;
    border-radius: 7px;
    padding: 8px 16px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #33373E;
    border-color: #5A6B78;
    color: #D8DCE3;
}
QPushButton:pressed { background-color: #23262B; }
QPushButton:disabled {
    color: #555B63;
    background-color: #1E2126;
    border-color: #282C32;
}
QPushButton#addButton, QPushButton#newBackupButton {
    background-color: #6A8490;
    color: #1C1E22;
    border: 1px solid #6A8490;
    font-weight: 600;
}
QPushButton#addButton:hover, QPushButton#newBackupButton:hover {
    background-color: #7B9BA6;
    border-color: #7B9BA6;
}
QPushButton#deleteButton, QPushButton#deleteBackupButton {
    color: #966565;
    border-color: #3E3030;
}
QPushButton#deleteButton:hover, QPushButton#deleteBackupButton:hover {
    background-color: #2A2224;
    border-color: #7A5050;
    color: #A87878;
}
QDialogButtonBox QPushButton { min-width: 84px; }

/* —— 对话框按钮组 —— */
QDialogButtonBox {
    background-color: transparent;
    spacing: 8px;
}
QDialogButtonBox QPushButton {
    background-color: #2A2D32;
    color: #B4B9C2;
    border: 1px solid #363A40;
    border-radius: 7px;
    padding: 8px 20px;
    font-weight: 500;
    min-width: 90px;
}
QDialogButtonBox QPushButton:hover {
    background-color: #33373E;
    border-color: #5A6B78;
    color: #D8DCE3;
}
QDialogButtonBox QPushButton:pressed { background-color: #23262B; }

/* —— 表单与标签 —— */
QLabel {
    background-color: transparent;
    color: #C0C6CF;
}
QFormLayout {
    background-color: transparent;
}
QGroupBox {
    background-color: transparent;
    border: 1px solid #2E3238;
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 12px;
    color: #C0C6CF;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #8FA8B0;
}
QCheckBox {
    background-color: transparent;
    color: #C0C6CF;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #363A40;
    border-radius: 4px;
    background-color: #222529;
}
QCheckBox::indicator:checked {
    background-color: #6A8490;
    border-color: #6A8490;
    image: none;
}
QCheckBox::indicator:hover { border-color: #5A6B78; }

/* —— 下拉框与数值框 —— */
QComboBox {
    background-color: #222529;
    border: 1px solid #2E3238;
    border-radius: 7px;
    padding: 6px 10px;
    color: #D8DCE3;
}
QComboBox:hover { border-color: #5A6B78; }
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #222529;
    color: #D8DCE3;
    border: 1px solid #2E3238;
    selection-background-color: #2E3A44;
    selection-color: #C8D4DB;
}
QSpinBox, QDoubleSpinBox {
    background-color: #222529;
    border: 1px solid #2E3238;
    border-radius: 7px;
    padding: 6px 10px;
    color: #D8DCE3;
}
QSpinBox:hover, QDoubleSpinBox:hover { border-color: #5A6B78; }
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #2A2D32;
    border: none;
    width: 16px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #33373E;
}

/* —— 进度条 —— */
QProgressBar {
    background-color: #222529;
    border: 1px solid #2E3238;
    border-radius: 6px;
    text-align: center;
    color: #C0C6CF;
}
QProgressBar::chunk {
    background-color: #6A8490;
    border-radius: 5px;
}

/* —— 滚动区与容器 —— */
QScrollArea {
    background-color: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}
QFrame {
    background-color: transparent;
    border: none;
}
QTabWidget::tab-bar {
    background: transparent;
}
QStatusBar QLabel {
    background-color: transparent;
    color: #7A808A;
}

/* —— 滚动条 —— */
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar::handle:vertical {
    background: #363A40; border-radius: 5px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: #5A6B78; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle:horizontal {
    background: #363A40; border-radius: 5px; min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: #5A6B78; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

/* —— 分割器 —— */
QSplitter::handle { background: #2E3238; }
QSplitter::handle:vertical { height: 2px; }
QSplitter::handle:horizontal { width: 2px; }

/* —— 右键菜单 —— */
QMenu {
    background-color: #222529;
    border: 1px solid #363A40;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item {
    padding: 7px 26px;
    border-radius: 5px;
    color: #C0C6CF;
}
QMenu::item:selected { background-color: #2E3A44; color: #C8D4DB; }
QMenu::separator { height: 1px; background: #2E3238; margin: 4px 8px; }

/* —— 消息框 —— */
QMessageBox { background-color: #222529; }
QMessageBox QLabel { color: #D8DCE3; }
QInputDialog { background-color: #1C1E22; }
QInputDialog QLabel { color: #D8DCE3; }

/* —— 状态栏 —— */
QStatusBar {
    background-color: #1C1E22;
    color: #7A808A;
    border-top: 1px solid #2E3238;
    font-size: 11px;
}
QStatusBar::item { border: none; }
QToolTip {
    background-color: #222529;
    color: #D8DCE3;
    border: 1px solid #363A40;
    padding: 4px 8px;
}
"""

class RegistryHandler:
    """注册表操作处理类"""
    def __init__(self):
        self.system_env_path = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
        self.user_env_path = r"Environment"
    
    def get_system_variables(self):
        """获取系统环境变量"""
        variables = {}
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, self.system_env_path, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                count = winreg.QueryInfoKey(key)[1]
                for i in range(count):
                    name, value, _ = winreg.EnumValue(key, i)
                    variables[name] = value
            return variables
        except PermissionError:
            return None  # 无管理员权限
        except Exception as e:
            print(f"读取系统变量失败: {e}")
            return {}
    
    def get_user_variables(self):
        """获取用户环境变量"""
        variables = {}
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.user_env_path, 0, winreg.KEY_READ) as key:
                count = winreg.QueryInfoKey(key)[1]
                for i in range(count):
                    name, value, _ = winreg.EnumValue(key, i)
                    variables[name] = value
            return variables
        except Exception as e:
            print(f"读取用户变量失败: {e}")
            return {}
    
    def set_system_variable(self, name, value):
        """设置系统环境变量"""
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, self.system_env_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)
            return True
        except PermissionError:
            return False  # 无管理员权限
        except Exception as e:
            print(f"设置系统变量失败: {e}")
            return False
    
    def set_user_variable(self, name, value):
        """设置用户环境变量"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.user_env_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)
            return True
        except Exception as e:
            print(f"设置用户变量失败: {e}")
            return False
    
    def delete_system_variable(self, name):
        """删除系统环境变量"""
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, self.system_env_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as key:
                winreg.DeleteValue(key, name)
            return True
        except PermissionError:
            return False  # 无管理员权限
        except FileNotFoundError:
            return True  # 变量不存在，视为删除成功
        except Exception as e:
            print(f"删除系统变量失败: {e}")
            return False
    
    def delete_user_variable(self, name):
        """删除用户环境变量"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.user_env_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, name)
            return True
        except FileNotFoundError:
            return True  # 变量不存在，视为删除成功
        except Exception as e:
            print(f"删除用户变量失败: {e}")
            return False

class BackupManager:
    """备份管理类"""
    def __init__(self):
        self.backup_dir = backup_dir
    
    def create_backup(self, description=""):
        """创建备份"""
        try:
            from datetime import datetime
            import time
            
            # 获取当前变量
            registry_handler = RegistryHandler()
            system_vars = registry_handler.get_system_variables()
            user_vars = registry_handler.get_user_variables()
            
            # 创建备份数据
            backup_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "description": description,
                "system_variables": system_vars or {},
                "user_variables": user_vars
            }
            
            # 生成备份文件名
            if description:
                filename = f"env_backup_{description}_{int(time.time())}.json"
            else:
                filename = f"env_backup_{int(time.time())}.json"
            
            # 保存备份文件
            backup_path = os.path.join(self.backup_dir, filename)
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=4)
            
            return True, backup_path
        except Exception as e:
            print(f"创建备份失败: {e}")
            return False, str(e)
    
    def get_backup_list(self):
        """获取备份列表"""
        backups = []
        try:
            from datetime import datetime
            
            for filename in os.listdir(self.backup_dir):
                if not filename.endswith('.json'):
                    continue
                filepath = os.path.join(self.backup_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception as e:
                    # 跳过损坏或无法解析的备份文件，避免影响整个列表
                    print(f"跳过损坏的备份文件 {filename}: {e}")
                    continue
                backups.append({
                    "filename": filename,
                    "path": filepath,
                    "timestamp": data.get("timestamp", ""),
                    "description": data.get("description", ""),
                    "system_count": len(data.get("system_variables", {})),
                    "user_count": len(data.get("user_variables", {}))
                })
            
            # 按时间倒序排序（时间缺失或无法解析的备份排到最后）
            def parse_time(item):
                try:
                    return datetime.strptime(item["timestamp"], "%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    return datetime.min
            backups.sort(key=parse_time, reverse=True)
            return backups
        except Exception as e:
            print(f"获取备份列表失败: {e}")
            return []
    
    def get_backup_details(self, backup_path):
        """获取备份详情"""
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"获取备份详情失败: {e}")
            return None
    
    def restore_backup(self, backup_path):
        """恢复备份"""
        try:
            # 读取备份文件
            with open(backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            system_vars = data.get("system_variables", {})
            user_vars = data.get("user_variables", {})
            
            # 验证备份文件有效性
            invalid_vars = []
            registry_handler = RegistryHandler()
            
            # 备份当前配置
            self.create_backup("pre_restore_auto_backup")
            
            # 恢复用户变量
            for name, value in user_vars.items():
                if not registry_handler.set_user_variable(name, value):
                    invalid_vars.append(f"User: {name}")
            
            # 恢复系统变量
            for name, value in system_vars.items():
                if not registry_handler.set_system_variable(name, value):
                    invalid_vars.append(f"System: {name}")
            
            return True, invalid_vars
        except Exception as e:
            print(f"恢复备份失败: {e}")
            return False, [str(e)]
    
    def delete_backup(self, backup_path):
        """删除备份"""
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
            return True
        except Exception as e:
            print(f"删除备份失败: {e}")
            return False

class EnvironmentVariableManager:
    """环境变量管理类"""
    def __init__(self):
        self.registry_handler = RegistryHandler()
        self.backup_manager = BackupManager()
    
    def get_variables(self, var_type):
        """获取环境变量"""
        if var_type == "system":
            return self.registry_handler.get_system_variables()
        elif var_type == "user":
            return self.registry_handler.get_user_variables()
        return {}
    
    def add_variable(self, var_type, name, value):
        """添加环境变量"""
        success = False
        if var_type == "system":
            success = self.registry_handler.set_system_variable(name, value)
        elif var_type == "user":
            success = self.registry_handler.set_user_variable(name, value)
        
        # 只有操作成功时才创建备份
        if success:
            self.backup_manager.create_backup(f"add_{name}")
        
        return success
    
    def update_variable(self, var_type, old_name, new_name, value):
        """更新环境变量"""
        success = False
        
        # 如果变量名改变，先删除旧变量
        if old_name != new_name:
            if var_type == "system":
                self.registry_handler.delete_system_variable(old_name)
            else:
                self.registry_handler.delete_user_variable(old_name)
        
        # 设置新变量
        success = self.add_variable(var_type, new_name, value)
        
        return success
    
    def delete_variable(self, var_type, name):
        """删除环境变量"""
        success = False
        if var_type == "system":
            success = self.registry_handler.delete_system_variable(name)
        elif var_type == "user":
            success = self.registry_handler.delete_user_variable(name)
        
        # 只有操作成功时才创建备份
        if success:
            self.backup_manager.create_backup(f"delete_{name}")
        
        return success
    
    def create_manual_backup(self, description=""):
        """手动创建备份"""
        return self.backup_manager.create_backup(description)
    
    def validate_variable(self, name, value):
        """验证变量有效性"""
        # 检查变量名是否为空
        if not name.strip():
            return False, "变量名不能为空"
        
        # 检查变量值是否为空
        if not value.strip():
            return False, "变量值不能为空"
        
        # 检查路径类变量
        if ("PATH" in name.upper() or "HOME" in name.upper() or "DIR" in name.upper() or "ROOT" in name.upper() or ":\\" in value or "/" in value):
            # PATHEXT是特殊变量，不进行路径检查
            if name.upper() == "PATHEXT":
                return True, ""
                
            # 所有包含PATH的变量或值中包含路径分隔符的变量，都拆分检查
            if "PATH" in name.upper() or os.pathsep in value:
                paths = value.split(os.pathsep)
                invalid_paths = []
                for path in paths:
                    path = path.strip()
                    if path and not is_valid_path(path):
                        invalid_paths.append(path)
                if invalid_paths:
                    return False, f"以下路径不存在: {', '.join(invalid_paths)}"
            else:
                # 普通路径变量检查
                if not is_valid_path(value):
                    return False, "路径不存在"
        
        return True, ""
    
    def validate_all_variables(self, var_type):
        """验证所有变量"""
        variables = self.get_variables(var_type)
        invalid_vars = []
        for name, value in variables.items():
            is_valid, message = self.validate_variable(name, value)
            if not is_valid:
                invalid_vars.append((name, message))
        return invalid_vars

class ColoredItemDelegate(QStyledItemDelegate):
    """列表项委托：文字颜色始终使用 item 前景色（选中/未选中都保持标红/标灰）"""
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        value = index.data(Qt.ForegroundRole)
        if value is not None and value.style() != Qt.NoBrush:
            option.palette.setBrush(QPalette.Text, value)
            option.palette.setBrush(QPalette.HighlightedText, value)
            option.palette.setBrush(QPalette.WindowText, value)

class VariableListWidget(QListWidget):
    """变量列表控件，支持拖拽和右键菜单"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.parent = parent
        self.setItemDelegate(ColoredItemDelegate(self))
        
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

class BackupManagerDialog(QDialog):
    """备份管理对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("备份管理")
        self.setMinimumSize(800, 600)
        
        self.backup_manager = BackupManager()
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # 顶部按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        self.refresh_button = QPushButton("刷新")
        self.new_backup_button = QPushButton("新建备份")
        self.new_backup_button.setObjectName("newBackupButton")
        self.restore_button = QPushButton("恢复")
        self.delete_button = QPushButton("删除")
        self.delete_button.setObjectName("deleteBackupButton")

        button_layout.addWidget(self.new_backup_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.restore_button)
        button_layout.addSpacing(10)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # 分割器
        splitter = QSplitter(Qt.Vertical)

        # 备份列表
        self.backup_tree = QTreeWidget()
        self.backup_tree.setHeaderLabels(["文件名", "时间", "描述", "系统变量数", "用户变量数"])
        self.backup_tree.setSelectionMode(QTreeWidget.SingleSelection)
        self.backup_tree.setAlternatingRowColors(True)
        self.backup_tree.setRootIsDecorated(False)
        self.backup_tree.setUniformRowHeights(True)

        # 备份详情
        self.detail_tree = QTreeWidget()
        self.detail_tree.setHeaderLabels(["变量类型", "变量名", "值"])
        self.detail_tree.setAlternatingRowColors(True)
        self.detail_tree.setRootIsDecorated(False)
        self.detail_tree.setUniformRowHeights(True)
        
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
        layout.addWidget(self.button_box)
        
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


class PathEditorDialog(QDialog):
    """多路径变量编辑器对话框"""
    def __init__(self, parent=None, value="", variable_name="PATH"):
        super().__init__(parent)
        self.setWindowTitle(f"编辑{variable_name}变量")
        self.setMinimumSize(600, 400)
        self.variable_name = variable_name
        
        # 布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # 路径列表
        self.path_list = QListWidget()
        self.path_list.setAlternatingRowColors(True)
        self.path_list.setUniformItemSizes(True)
        self.path_list.setItemDelegate(ColoredItemDelegate(self))
        layout.addWidget(self.path_list)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("添加路径")
        self.edit_button = QPushButton("编辑路径")
        self.delete_button = QPushButton("删除路径")
        self.up_button = QPushButton("上移")
        self.down_button = QPushButton("下移")
        self.browse_button = QPushButton("浏览文件夹")
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.up_button)
        button_layout.addWidget(self.down_button)
        button_layout.addWidget(self.browse_button)
        
        layout.addLayout(button_layout)
        
        # 按钮盒
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(self.button_box)
        
        # 连接信号
        self.add_button.clicked.connect(self.add_path)
        self.edit_button.clicked.connect(self.edit_path)
        self.delete_button.clicked.connect(self.delete_path)
        self.up_button.clicked.connect(self.move_up)
        self.down_button.clicked.connect(self.move_down)
        self.browse_button.clicked.connect(self.browse_folder)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        # 初始化路径列表
        self.load_paths(value)
        
        # 更新按钮状态
        self.update_buttons()
    
    def load_paths(self, value):
        """加载路径到列表"""
        if value:
            paths = value.split(os.pathsep)
            for path in paths:
                if path.strip():
                    item = QListWidgetItem(path.strip())
                    
                    # 验证路径有效性
                    if is_valid_path(path.strip()):
                        item.setForeground(QColor("#7BA07B"))
                    else:
                        item.setForeground(QColor("#966565"))
                    
                    self.path_list.addItem(item)
    
    def add_path(self):
        """添加路径"""
        path, ok = QInputDialog.getText(self, "添加路径", "请输入路径:")
        if ok and path.strip():
            item = QListWidgetItem(path.strip())
            
            # 验证路径有效性
            if is_valid_path(path.strip()):
                item.setForeground(QColor("#7BA07B"))
            else:
                item.setForeground(QColor("#966565"))
            
            self.path_list.addItem(item)
            self.update_buttons()
    
    def edit_path(self):
        """编辑路径"""
        current_item = self.path_list.currentItem()
        if current_item:
            old_path = current_item.text()
            new_path, ok = QInputDialog.getText(self, "编辑路径", "请输入新路径:", text=old_path)
            if ok and new_path.strip():
                current_item.setText(new_path.strip())
                
                # 验证路径有效性
                if is_valid_path(new_path.strip()):
                    current_item.setForeground(QColor("#7BA07B"))
                else:
                    current_item.setForeground(QColor("#966565"))
    
    def delete_path(self):
        """删除路径"""
        # 获取当前选中项的行号
        current_row = self.path_list.currentRow()
        
        # 确保有选中项
        if current_row >= 0:
            # 删除选中项
            self.path_list.takeItem(current_row)
            
            # 如果删除后还有项，选中下一项
            if self.path_list.count() > 0:
                new_row = min(current_row, self.path_list.count() - 1)
                self.path_list.setCurrentRow(new_row)
            
            # 更新按钮状态
            self.update_buttons()
    
    def move_up(self):
        """上移路径"""
        current_row = self.path_list.currentRow()
        if current_row > 0:
            current_item = self.path_list.takeItem(current_row)
            self.path_list.insertItem(current_row - 1, current_item)
            self.path_list.setCurrentRow(current_row - 1)
            self.update_buttons()
    
    def move_down(self):
        """下移路径"""
        current_row = self.path_list.currentRow()
        if current_row < self.path_list.count() - 1:
            current_item = self.path_list.takeItem(current_row)
            self.path_list.insertItem(current_row + 1, current_item)
            self.path_list.setCurrentRow(current_row + 1)
            self.update_buttons()
    
    def browse_folder(self):
        """浏览文件夹"""
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder_path:
            # 如果有选中项，替换它；否则添加新项
            current_item = self.path_list.currentItem()
            if current_item:
                current_item.setText(folder_path)
                
                # 验证路径有效性
                if is_valid_path(folder_path):
                    current_item.setForeground(QColor("#7BA07B"))
                else:
                    current_item.setForeground(QColor("#966565"))
            else:
                item = QListWidgetItem(folder_path)
                item.setForeground(QColor("#7BA07B"))
                self.path_list.addItem(item)
                self.update_buttons()
    
    def update_buttons(self):
        """更新按钮状态"""
        count = self.path_list.count()
        current_row = self.path_list.currentRow()
        
        # 确保current_row的有效性
        if current_row < 0 and count > 0:
            # 如果没有选中项但列表不为空，默认选中第一个
            self.path_list.setCurrentRow(0)
            current_row = 0
        
        has_selection = current_row >= 0
        can_move_up = has_selection and current_row > 0
        can_move_down = has_selection and current_row < count - 1
        self.edit_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)
        self.up_button.setEnabled(can_move_up)
        self.down_button.setEnabled(can_move_down)
    def get_path_string(self):
        """获取路径字符串"""
        paths = []
        for i in range(self.path_list.count()):
            paths.append(self.path_list.item(i).text())
        return os.pathsep.join(paths)

class MainWindow(QMainWindow):
    """主窗口类"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Windows系统变量管理工具")
        self.setMinimumSize(800, 600)
        
        # 初始化环境变量管理器
        self.env_manager = EnvironmentVariableManager()
        self.current_var_type = "user"  # 默认显示用户变量
        
        # 创建主界面
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # 主布局
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(18, 14, 18, 14)
        self.main_layout.setSpacing(10)

        # 顶部标题区
        header_widget = QWidget()
        header_widget.setObjectName("headerWidget")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(2, 0, 2, 0)
        header_layout.setSpacing(12)

        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        self.title_label = QLabel("环境变量管理  ·  ENV MANAGER")
        self.title_label.setObjectName("HeaderTitle")
        self.subtitle_label = QLabel("管理用户与系统环境变量  /  多路径可视化编辑  /  操作自动备份")
        self.subtitle_label.setObjectName("HeaderSubtitle")
        title_block.addWidget(self.title_label)
        title_block.addWidget(self.subtitle_label)
        header_layout.addLayout(title_block)
        header_layout.addStretch()

        # 权限状态徽标
        self.perm_badge = QLabel("权限检测中")
        self.perm_badge.setObjectName("permBadge")
        header_layout.addWidget(self.perm_badge)

        self.main_layout.addWidget(header_widget)

        # 标签切换区
        self.tab_widget = QTabWidget()
        self.user_tab = QWidget()
        self.system_tab = QWidget()
        
        self.tab_widget.addTab(self.user_tab, "用户变量")
        self.tab_widget.addTab(self.system_tab, "系统变量 (管理员)")
        
        # 用户变量界面
        self.user_layout = QVBoxLayout(self.user_tab)
        self.user_layout.setContentsMargins(4, 6, 4, 4)
        self.user_layout.setSpacing(8)

        # 用户变量搜索框
        self.user_search_layout = QHBoxLayout()
        self.user_search_layout.setSpacing(8)
        self.user_search_label = QLabel("搜索")
        self.user_search_label.setObjectName("HeaderSubtitle")
        self.user_search_input = QLineEdit()
        self.user_search_input.setPlaceholderText("输入变量名或值进行搜索...")
        self.user_search_input.textChanged.connect(self.load_variables)

        self.user_search_layout.addWidget(self.user_search_label)
        self.user_search_layout.addWidget(self.user_search_input)

        self.user_list_widget = VariableListWidget(self)
        self.user_layout.addLayout(self.user_search_layout)
        self.user_layout.addWidget(self.user_list_widget)

        # 系统变量界面
        self.system_layout = QVBoxLayout(self.system_tab)
        self.system_layout.setContentsMargins(4, 6, 4, 4)
        self.system_layout.setSpacing(8)

        # 系统变量搜索框
        self.system_search_layout = QHBoxLayout()
        self.system_search_layout.setSpacing(8)
        self.system_search_label = QLabel("搜索")
        self.system_search_label.setObjectName("HeaderSubtitle")
        self.system_search_input = QLineEdit()
        self.system_search_input.setPlaceholderText("输入变量名或值进行搜索...")
        self.system_search_input.textChanged.connect(self.load_variables)

        self.system_search_layout.addWidget(self.system_search_label)
        self.system_search_layout.addWidget(self.system_search_input)

        self.system_list_widget = VariableListWidget(self)
        self.system_layout.addLayout(self.system_search_layout)
        self.system_layout.addWidget(self.system_list_widget)

        # 功能按钮区
        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(2, 0, 2, 0)
        self.button_layout.setSpacing(8)
        self.add_button = QPushButton("添加变量")
        self.add_button.setObjectName("addButton")
        self.edit_button = QPushButton("编辑变量")
        self.delete_button = QPushButton("删除变量")
        self.delete_button.setObjectName("deleteButton")
        self.validate_button = QPushButton("批量验证")
        self.sort_button = QPushButton("一键整理")
        self.backup_button = QPushButton("备份管理")

        self.button_layout.addWidget(self.add_button)
        self.button_layout.addWidget(self.edit_button)
        self.button_layout.addWidget(self.delete_button)
        self.button_layout.addSpacing(14)
        self.button_layout.addWidget(self.validate_button)
        self.button_layout.addWidget(self.sort_button)
        self.button_layout.addWidget(self.backup_button)
        self.button_layout.addStretch()
        
        # 添加到主布局
        self.main_layout.addWidget(self.tab_widget)
        self.main_layout.addLayout(self.button_layout)
        
        # 连接信号
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.add_button.clicked.connect(self.show_add_variable_dialog)
        self.edit_button.clicked.connect(self.show_edit_variable_dialog)
        self.delete_button.clicked.connect(self.delete_variable)
        self.validate_button.clicked.connect(self.validate_all_variables)
        self.sort_button.clicked.connect(self.sort_variables)
        self.backup_button.clicked.connect(self.show_backup_manager)
        
        # 加载变量
        self.load_variables()
        
        # 检查系统变量权限
        self.check_system_permission()
    
    def on_tab_changed(self, index):
        """标签切换事件"""
        if index == 0:
            self.current_var_type = "user"
        else:
            self.current_var_type = "system"
        self.load_variables()
    
    def load_variables(self):
        """加载变量列表"""
        # 获取当前标签页的列表控件
        list_widget = self.user_list_widget if self.current_var_type == "user" else self.system_list_widget
        
        # 清空列表
        list_widget.clear()
        
        # 获取变量
        variables = self.env_manager.get_variables(self.current_var_type)
        if variables is None:
            # 没有系统变量权限
            item = QListWidgetItem("没有权限访问系统变量，请以管理员身份运行程序")
            item.setForeground(QColor("#966565"))
            list_widget.addItem(item)
            self.statusBar().showMessage("无权限访问系统变量")
            return
        
        # 获取搜索关键词
        search_input = self.user_search_input if self.current_var_type == "user" else self.system_search_input
        search_keyword = search_input.text().lower()
        
        # 过滤变量
        filtered_vars = {}
        for name, value in variables.items():
            if search_keyword in name.lower() or search_keyword in value.lower():
                filtered_vars[name] = value
        
        # 按变量名排序
        sorted_vars = sorted(filtered_vars.items(), key=lambda x: x[0])
        
        # 添加到列表
        for name, value in sorted_vars:
            # 验证变量有效性
            is_valid, message = self.env_manager.validate_variable(name, value)
            
            # 创建列表项
            item_text = f"{name} = {value}"
            item = QListWidgetItem(item_text)
            
            # 设置变量样式：有效变量用默认文字色，无效变量标红
            if not is_valid:
                item.setForeground(QColor("#966565"))
            else:
                item.setForeground(QColor("#C0C6CF"))
            
            # 存储变量名和值
            item.setData(Qt.UserRole, (name, value))
            
            list_widget.addItem(item)

        # 状态栏统计
        scope = "用户" if self.current_var_type == "user" else "系统"
        total = len(variables)
        shown = len(sorted_vars)
        if search_keyword:
            self.statusBar().showMessage(f"{scope}作用域  ·  显示 {shown} / {total} 个变量")
        else:
            self.statusBar().showMessage(f"{scope}作用域  ·  共 {total} 个变量")
    
    def check_system_permission(self):
        """检查系统变量权限"""
        system_vars = self.env_manager.get_variables("system")
        if system_vars is None:
            self.perm_badge.setText("普通用户")
            self.perm_badge.setStyleSheet(
                "QLabel#permBadge { color:#9AA0AA; border:1px solid #4A4E55; "
                "border-radius:11px; padding:3px 14px; font-size:11px; font-weight:600; }"
            )
            QMessageBox.warning(self, "权限提示", "您没有管理员权限，无法修改系统变量。")
        else:
            self.perm_badge.setText("管理员")
            self.perm_badge.setStyleSheet(
                "QLabel#permBadge { color:#7BA07B; border:1px solid #4A5A4A; "
                "border-radius:11px; padding:3px 14px; font-size:11px; font-weight:600; }"
            )
    
    def show_add_variable_dialog(self):
        """显示添加变量对话框"""
        # 首先显示名称输入对话框
        name, ok = QInputDialog.getText(self, "添加变量", "请输入变量名:")
        
        if not ok or not name.strip():
            return
            
        name = name.strip().upper() if name.strip().upper() == "PATH" else name.strip()
            
        # 检查变量名是否已存在
        current_vars = self.env_manager.get_variables(self.current_var_type)
        if name in current_vars:
            QMessageBox.warning(self, "错误", "变量名已存在")
            return
        
        # 询问用户是否为多路径变量
        is_multi_path = False
        if QMessageBox.question(self, "确认", "是否为多路径变量？", 
                               QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            is_multi_path = True
        
        if name.upper() == "PATH" or is_multi_path:
            # 使用多路径变量编辑器
            dialog = PathEditorDialog(self, "", name)
            if dialog.exec_():
                value = dialog.get_path_string()
                
                # 非路径相关的基础校验（空值等）
                if not name.strip() or not value.strip():
                    QMessageBox.warning(self, "验证失败", "变量名和值不能为空")
                    return
                    
                # 添加变量（不再弹窗阻止路径不存在，由列表标红提示）
                if self.env_manager.add_variable(self.current_var_type, name, value):
                    is_valid, message = self.env_manager.validate_variable(name, value)
                    if not is_valid:
                        self.statusBar().showMessage(f"变量已保存，但部分路径无效: {message}")
                    else:
                        QMessageBox.information(self, "成功", "变量添加成功")
                    self.load_variables()
                else:
                    QMessageBox.warning(self, "失败", "添加变量失败，请检查权限")
        else:
            # 使用普通变量编辑器
            dialog = AddEditVariableDialog(self, self.current_var_type, name, "")
            if dialog.exec_():
                _, value = dialog.get_data()
                
                # 检查是否为多路径变量
                is_multi_path = False
                if os.pathsep in value:
                    paths = value.split(os.pathsep)
                    for path in paths:
                        if path.strip() and ("\\" in path or "/" in path):
                            is_multi_path = True
                            break
                
                if is_multi_path:
                    # 如果是多路径变量，使用PathEditorDialog重新编辑
                    edit_dialog = PathEditorDialog(self, value, name)
                    if edit_dialog.exec_():
                        value = edit_dialog.get_path_string()
                
                # 非路径相关的基础校验（空值等）
                if not name.strip() or not value.strip():
                    QMessageBox.warning(self, "验证失败", "变量名和值不能为空")
                    return
                    
                # 添加变量（不再弹窗阻止路径不存在，由列表标红提示）
                if self.env_manager.add_variable(self.current_var_type, name, value):
                    is_valid, message = self.env_manager.validate_variable(name, value)
                    if not is_valid:
                        self.statusBar().showMessage(f"变量已保存，但路径无效: {message}")
                    else:
                        QMessageBox.information(self, "成功", "变量添加成功")
                    self.load_variables()
                else:
                    QMessageBox.warning(self, "失败", "添加变量失败，请检查权限")
    
    def show_edit_variable_dialog(self):
        """显示编辑变量对话框"""
        # 获取当前选中项
        list_widget = self.user_list_widget if self.current_var_type == "user" else self.system_list_widget
        selected_item = list_widget.currentItem()
        
        if not selected_item:
            QMessageBox.warning(self, "警告", "请选择要编辑的变量")
            return
        
        # 获取变量名和值
        name, value = selected_item.data(Qt.UserRole)
        
        # 根据变量值判断是否为多路径变量（包含分号分隔的路径）
        is_multi_path = False
        if os.pathsep in value:
            # 检查是否包含有效的路径分隔符和路径格式
            paths = value.split(os.pathsep)
            for path in paths:
                if path.strip() and ("\\" in path or "/" in path):
                    is_multi_path = True
                    break
        
        # 使用多路径编辑器（PathEditorDialog）的情况：
        # 1. 变量名为PATH
        # 2. 变量值包含分号分隔的有效路径
        if name.upper() == "PATH" or is_multi_path:
            # 使用多路径变量编辑器
            dialog = PathEditorDialog(self, value, name)
            if dialog.exec_():
                new_value = dialog.get_path_string()
                new_name = name  # 多路径变量名不能更改
                
                # 非路径相关的基础校验（空值等）
                if not new_name.strip() or not new_value.strip():
                    QMessageBox.warning(self, "验证失败", "变量名和值不能为空")
                    return
                
                # 更新变量（不再弹窗阻止路径不存在，由列表标红提示）
                if self.env_manager.update_variable(self.current_var_type, name, new_name, new_value):
                    is_valid, message = self.env_manager.validate_variable(new_name, new_value)
                    if not is_valid:
                        self.statusBar().showMessage(f"变量已更新，但部分路径无效: {message}")
                    else:
                        QMessageBox.information(self, "成功", "变量更新成功")
                    self.load_variables()
                else:
                    QMessageBox.warning(self, "失败", "更新变量失败，请检查权限")
        else:
            # 使用普通变量编辑器
            dialog = AddEditVariableDialog(self, self.current_var_type, name, value)
            if dialog.exec_():
                new_name, new_value = dialog.get_data()
                
                # 非路径相关的基础校验（空值等）
                if not new_name.strip() or not new_value.strip():
                    QMessageBox.warning(self, "验证失败", "变量名和值不能为空")
                    return
                
                # 检查变量名是否已存在（排除当前变量）
                current_vars = self.env_manager.get_variables(self.current_var_type)
                if new_name != name and new_name in current_vars:
                    QMessageBox.warning(self, "错误", "变量名已存在")
                    return
                
                # 更新变量（不再弹窗阻止路径不存在，由列表标红提示）
                if self.env_manager.update_variable(self.current_var_type, name, new_name, new_value):
                    is_valid, message = self.env_manager.validate_variable(new_name, new_value)
                    if not is_valid:
                        self.statusBar().showMessage(f"变量已更新，但路径无效: {message}")
                    else:
                        QMessageBox.information(self, "成功", "变量更新成功")
                    self.load_variables()
                else:
                    QMessageBox.warning(self, "失败", "更新变量失败，请检查权限")
    
    def delete_variable(self):
        """删除变量"""
        # 获取当前选中项
        list_widget = self.user_list_widget if self.current_var_type == "user" else self.system_list_widget
        selected_item = list_widget.currentItem()
        
        if not selected_item:
            QMessageBox.warning(self, "警告", "请选择要删除的变量")
            return
        
        # 获取变量名
        name, _ = selected_item.data(Qt.UserRole)
        
        # 二次确认
        reply = QMessageBox.question(
            self, "确认删除", f"确定要删除变量 '{name}' 吗?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 删除变量
            if self.env_manager.delete_variable(self.current_var_type, name):
                QMessageBox.information(self, "成功", "变量删除成功")
                self.load_variables()
            else:
                QMessageBox.warning(self, "失败", "删除变量失败，请检查权限")
    
    def validate_all_variables(self):
        """批量验证变量"""
        invalid_vars = self.env_manager.validate_all_variables(self.current_var_type)
        
        if invalid_vars:
            # 显示无效变量
            message = "以下变量无效:\n"
            for name, reason in invalid_vars:
                message += f"{name}: {reason}\n"
            QMessageBox.warning(self, "验证结果", message)
        else:
            QMessageBox.information(self, "验证结果", "所有变量均有效")
    
    def sort_variables(self):
        """一键整理变量（按变量名排序）"""
        # 由于load_variables已经默认按变量名排序，这里只需要刷新列表
        self.load_variables()
        QMessageBox.information(self, "成功", "变量已按名称升序排序")
    
    def validate_selected_variable(self):
        """验证选中变量"""
        # 获取当前选中项
        list_widget = self.user_list_widget if self.current_var_type == "user" else self.system_list_widget
        selected_item = list_widget.currentItem()
        
        if not selected_item:
            QMessageBox.warning(self, "警告", "请选择要验证的变量")
            return
        
        # 获取变量名和值
        name, value = selected_item.data(Qt.UserRole)
        
        # 验证变量
        is_valid, message = self.env_manager.validate_variable(name, value)
        
        if is_valid:
            QMessageBox.information(self, "验证结果", "变量有效")
        else:
            QMessageBox.warning(self, "验证结果", f"变量无效: {message}")
    
    def show_backup_manager(self):
        """显示备份管理对话框"""
        dialog = BackupManagerDialog(self)
        dialog.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    # 全局字体
    font = QFont("Microsoft YaHei UI", 9)
    app.setFont(font)
    window = MainWindow()
    window.resize(980, 700)
    window.show()
    sys.exit(app.exec_())
