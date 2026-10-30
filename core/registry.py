"""Windows 注册表环境变量底层：权限、枚举、读写、删除、变更广播。"""

from __future__ import annotations

import ctypes
import threading
from dataclasses import dataclass, asdict

import winreg

USER_SUBKEY = "Environment"
SYSTEM_SUBKEY = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"

SCOPE_USER = "user"
SCOPE_SYSTEM = "system"

# 系统环境变量位于 64 位注册表视图，必须显式指定，
# 避免在 32 位进程里读到 WOW64 重定向出来的空视图。
_WOW64_64KEY = getattr(winreg, "KEY_WOW64_64KEY", 0)


@dataclass(frozen=True)
class Var:
    """一个环境变量。scope 为 "user"（用户）或 "system"（系统）。"""

    scope: str
    name: str
    value: str
    kind: int  # winreg.REG_SZ 或 winreg.REG_EXPAND_SZ

    def to_dict(self) -> dict:
        return asdict(self)


def is_admin() -> bool:
    """当前进程是否以管理员身份运行。"""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _root_and_subkey(scope: str) -> tuple[int, str]:
    if scope == SCOPE_USER:
        return winreg.HKEY_CURRENT_USER, USER_SUBKEY
    if scope == SCOPE_SYSTEM:
        return winreg.HKEY_LOCAL_MACHINE, SYSTEM_SUBKEY
    raise ValueError(f"未知范围：{scope}")


def _read_flags(scope: str) -> int:
    return winreg.KEY_READ | (_WOW64_64KEY if scope == SCOPE_SYSTEM else 0)


def _write_flags(scope: str) -> int:
    return winreg.KEY_SET_VALUE | (_WOW64_64KEY if scope == SCOPE_SYSTEM else 0)


def _value_exists(scope: str, name: str) -> bool:
    """某范围内是否存在同名值（不区分大小写，由注册表语义保证）"""
    root, subkey = _root_and_subkey(scope)
    try:
        with winreg.OpenKey(root, subkey, 0, _read_flags(scope)) as key:
            winreg.QueryValueEx(key, name)
        return True
    except OSError:
        return False


def read_var(scope: str, name: str) -> tuple[str, int] | None:
    """读取单个环境变量的当前值与类型；不存在返回 None。

    用于保存后的读回校验，确保写入对系统编辑器与新进程真实可见。
    """
    root, subkey = _root_and_subkey(scope)
    try:
        with winreg.OpenKey(root, subkey, 0, _read_flags(scope)) as key:
            value, kind = winreg.QueryValueEx(key, name)
            if isinstance(value, str):
                return value, kind
            return None
    except OSError:
        return None


def list_vars(scope: str) -> list[Var]:
    """枚举指定范围内的全部字符串环境变量，按名称排序。"""
    root, subkey = _root_and_subkey(scope)
    try:
        key = winreg.OpenKey(root, subkey, 0, _read_flags(scope))
    except PermissionError as exc:
        raise RuntimeError("读取系统变量需要管理员权限") from exc
    except OSError as exc:
        raise RuntimeError(f"读取注册表失败：{exc}") from exc
    result: list[Var] = []
    with key:
        count = winreg.QueryInfoKey(key)[1]
        for index in range(count):
            try:
                name, value, kind = winreg.EnumValue(key, index)
            except OSError:
                break
            if kind not in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
                continue
            if not isinstance(value, str):
                continue
            result.append(Var(scope, name, value, kind))
    result.sort(key=lambda v: v.name.casefold())
    return result


def _set_raw(scope: str, name: str, value: str, kind: int) -> None:
    """底层写入，不做备份、不广播。"""
    root, subkey = _root_and_subkey(scope)
    try:
        with winreg.OpenKey(root, subkey, 0, _write_flags(scope)) as key:
            winreg.SetValueEx(key, name, 0, kind, value)
    except PermissionError as exc:
        raise RuntimeError("写入系统变量需要管理员权限") from exc
    except OSError as exc:
        raise RuntimeError(f"写入注册表失败：{exc}") from exc


def _delete_raw(scope: str, name: str) -> None:
    """底层删除，不做备份、不广播。"""
    root, subkey = _root_and_subkey(scope)
    try:
        with winreg.OpenKey(root, subkey, 0, _write_flags(scope)) as key:
            winreg.DeleteValue(key, name)
    except FileNotFoundError:
        return
    except PermissionError as exc:
        raise RuntimeError("删除系统变量需要管理员权限") from exc
    except OSError as exc:
        raise RuntimeError(f"删除注册表值失败：{exc}") from exc


def set_var(scope: str, name: str, value: str, kind: int | None = None) -> None:
    """写入（新建或更新）一个环境变量，应用成功后自动备份当前全量状态。

    kind 省略时自动推断：值中含 "%" 视为 REG_EXPAND_SZ。
    """
    if kind is None:
        kind = winreg.REG_EXPAND_SZ if "%" in value else winreg.REG_SZ
    op = "update" if _value_exists(scope, name) else "add"
    _set_raw(scope, name, value, kind)
    # 只有应用成功后才备份（快照为应用后的最新状态）；写入失败不产生备份
    from core import backup_store  # 函数内导入，避免与 backup_store 循环依赖

    backup_store.auto_backup(f"{op}_{name}")


def delete_var(scope: str, name: str) -> None:
    """删除一个环境变量，应用成功后自动备份当前全量状态。"""
    _delete_raw(scope, name)
    from core import backup_store  # 函数内导入，避免与 backup_store 循环依赖

    backup_store.auto_backup(f"delete_{name}")


# ---------------------------------------------------------------------------
# 名称校验 / 变更广播
# ---------------------------------------------------------------------------


def validate_name(
    name: str, scope: str, existing: list[Var], editing: str | None = None
) -> str | None:
    """校验变量名，返回错误信息；合法返回 None。editing 为重命名前的原名。"""
    n = name.strip()
    if not n:
        return "变量名不能为空"
    if "=" in n or "\x00" in n:
        return "变量名不能包含 “=” 等非法字符"
    for v in existing:
        if v.scope != scope:
            continue
        same_var = editing is not None and v.name.casefold() == editing.casefold()
        if not same_var and v.name.casefold() == n.casefold():
            return "该范围内已存在同名变量"
    return None


def broadcast_change() -> None:
    """在后台线程广播 WM_SETTINGCHANGE，使资源管理器等立即感知变更。"""
    threading.Thread(target=_broadcast, daemon=True).start()


def _broadcast() -> None:
    try:
        hwnd_broadcast = 0xFFFF
        wm_settingchange = 0x001A
        smto_abortifhung = 0x0002
        result = ctypes.c_ulong()
        ctypes.windll.user32.SendMessageTimeoutW(
            hwnd_broadcast,
            wm_settingchange,
            0,
            "Environment",
            smto_abortifhung,
            1000,
            ctypes.byref(result),
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 组合操作（备份 → 写注册表 → 广播）
# ---------------------------------------------------------------------------


def add_variable(scope: str, name: str, value: str, kind: int | None = None) -> None:
    """新增变量：自动备份 → 写入 → 广播变更。"""
    set_var(scope, name, value, kind)
    broadcast_change()


def update_variable(
    scope: str, old_name: str, new_name: str, value: str, kind: int | None = None
) -> None:
    """更新变量（支持重命名）：自动备份 → 写新名 → 删旧名 → 广播变更。

    重命名仅大小写变化时注册表按同名处理，无需删除。
    """
    set_var(scope, new_name, value, kind)
    if old_name.casefold() != new_name.casefold():
        _delete_raw(scope, old_name)
    broadcast_change()


def remove_variable(scope: str, name: str) -> None:
    """删除变量：自动备份 → 删除 → 广播变更。"""
    delete_var(scope, name)
    broadcast_change()
