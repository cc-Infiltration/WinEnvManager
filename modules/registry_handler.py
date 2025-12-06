import winreg

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