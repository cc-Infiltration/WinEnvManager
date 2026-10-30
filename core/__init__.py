"""Windows 环境变量数据层：注册表读写、PATH 多值处理、备份持久化、设置存储。

模块划分：
- registry       注册表底层读写、Var 数据类、名称校验、变更广播、组合操作
- path_values    PATH 类多值变量的拆分 / 合并 / 校验
- backup_store   全量快照、自动备份（节流 / 去重 / 上限）、恢复、导入导出
- settings_store 应用数据目录、设置持久化

公共 API 全部从本包顶层 re-export，使用方 `import core as app_core` 即可。
"""

from core.settings_store import (
    APP_DIR,
    BACKUPS_DIR,
    SETTINGS_PATH,
    DEFAULT_SETTINGS,
    ensure_dirs,
    load_settings,
    save_settings,
)
from core.path_values import (
    VAR_SEP,
    check_path_entry,
    is_multi_path_value,
    is_path_var,
    join_path_value,
    normalize_path_value,
    split_path_value,
    validate_path_value,
)
from core.registry import (
    SCOPE_SYSTEM,
    SCOPE_USER,
    USER_SUBKEY,
    SYSTEM_SUBKEY,
    Var,
    add_variable,
    broadcast_change,
    delete_var,
    is_admin,
    list_vars,
    read_var,
    remove_variable,
    set_var,
    update_variable,
    validate_name,
)
from core.backup_store import (
    auto_backup,
    create_backup,
    delete_backup,
    export_backup,
    list_backups,
    load_backup,
    read_backup_raw,
    restore_backup,
    snapshot_vars,
    write_backup_raw,
)

__all__ = [
    # settings_store
    "APP_DIR", "BACKUPS_DIR", "SETTINGS_PATH", "DEFAULT_SETTINGS",
    "ensure_dirs", "load_settings", "save_settings",
    # path_values
    "VAR_SEP", "check_path_entry", "is_multi_path_value", "is_path_var",
    "join_path_value", "normalize_path_value", "split_path_value",
    "validate_path_value",
    # registry
    "SCOPE_SYSTEM", "SCOPE_USER", "USER_SUBKEY", "SYSTEM_SUBKEY", "Var",
    "add_variable", "broadcast_change", "delete_var", "is_admin", "list_vars",
    "read_var", "remove_variable", "set_var", "update_variable", "validate_name",
    # backup_store
    "auto_backup", "create_backup", "delete_backup", "export_backup",
    "list_backups", "load_backup", "read_backup_raw", "restore_backup",
    "snapshot_vars", "write_backup_raw",
]
