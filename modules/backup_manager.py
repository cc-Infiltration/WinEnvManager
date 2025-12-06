import os
import json
import time
from datetime import datetime

class BackupManager:
    """备份管理类"""
    def __init__(self):
        self.backup_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backup')
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
    
    def create_backup(self, description=""):
        """创建备份"""
        try:
            # 导入RegistryHandler获取当前变量
            from .registry_handler import RegistryHandler
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
            for filename in os.listdir(self.backup_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.backup_dir, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    backups.append({
                        "filename": filename,
                        "path": filepath,
                        "timestamp": data.get("timestamp", ""),
                        "description": data.get("description", ""),
                        "system_count": len(data.get("system_variables", {})),
                        "user_count": len(data.get("user_variables", {}))
                    })
            
            # 按时间倒序排序
            backups.sort(key=lambda x: datetime.strptime(x["timestamp"], "%Y-%m-%d %H:%M:%S"), reverse=True)
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
            from .registry_handler import RegistryHandler
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