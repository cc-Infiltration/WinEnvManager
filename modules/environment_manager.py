import os

class EnvironmentVariableManager:
    """环境变量管理类"""
    def __init__(self):
        # 延迟导入，避免循环导入问题
        from .registry_handler import RegistryHandler
        from .backup_manager import BackupManager
        
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
        # 自动备份
        self.backup_manager.create_backup(f"add_{name}")
        
        if var_type == "system":
            return self.registry_handler.set_system_variable(name, value)
        elif var_type == "user":
            return self.registry_handler.set_user_variable(name, value)
        return False
    
    def update_variable(self, var_type, old_name, new_name, value):
        """更新环境变量"""
        # 自动备份
        self.backup_manager.create_backup(f"update_{old_name}")
        
        # 如果变量名改变，先删除旧变量
        if old_name != new_name:
            if var_type == "system":
                self.registry_handler.delete_system_variable(old_name)
            else:
                self.registry_handler.delete_user_variable(old_name)
        
        # 设置新变量
        return self.add_variable(var_type, new_name, value)
    
    def delete_variable(self, var_type, name):
        """删除环境变量"""
        # 自动备份
        self.backup_manager.create_backup(f"delete_{name}")
        
        if var_type == "system":
            return self.registry_handler.delete_system_variable(name)
        elif var_type == "user":
            return self.registry_handler.delete_user_variable(name)
        return False
    
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
            # 如果是PATH变量，拆分检查
            if name.upper() == "PATH":
                paths = value.split(os.pathsep)
                invalid_paths = []
                for path in paths:
                    if path and not os.path.exists(path.strip()):
                        invalid_paths.append(path.strip())
                if invalid_paths:
                    return False, f"以下路径不存在: {', '.join(invalid_paths)}"
            else:
                # 普通路径变量检查
                if not os.path.exists(value.strip()):
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