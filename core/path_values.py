"""PATH 类多值变量：拆分 / 合并 / 逐条路径有效性校验。"""

from __future__ import annotations

import os
import threading

# 多值变量分隔符（Windows 下为 ";"）
VAR_SEP = os.pathsep

# UNC 路径存在性探测超时（秒），防止不可达的网络地址卡住调用方
_UNC_PROBE_TIMEOUT = 1.5


def is_path_var(name: str) -> bool:
    """是否为路径类变量（名称含 "PATH"，不区分大小写，如 Path / PATH）。"""
    return "PATH" in name.upper()


def is_multi_path_value(value: str) -> bool:
    """值是否表现为多路径：含分隔符，且至少一条含路径斜杠。"""
    if VAR_SEP not in value:
        return False
    return any(("\\" in p or "/" in p) for p in value.split(VAR_SEP) if p.strip())


def split_path_value(value: str, *, drop_empty: bool = True) -> list[str]:
    """把多值变量按 os.pathsep 拆分为条目列表，每条去除首尾空白。

    drop_empty=True 时丢弃空白条目（与原生工具的编辑列表一致）。
    """
    if not value:
        return []
    parts = [p.strip() for p in value.split(VAR_SEP)]
    if drop_empty:
        return [p for p in parts if p]
    return parts


def join_path_value(paths) -> str:
    """把条目列表合并为一个变量值（os.pathsep 连接）。"""
    return VAR_SEP.join(str(p) for p in paths)


def normalize_path_value(value: str) -> str:
    """规范化多值变量：拆分 → 去空白/空条目 → 重新合并。"""
    return join_path_value(split_path_value(value))


def _probe_exists(path: str) -> bool:
    """带超时的存在性探测，用于 UNC 路径，避免长时间阻塞。"""
    result = [False]

    def _check() -> None:
        try:
            result[0] = os.path.exists(path)
        except Exception:
            result[0] = False

    t = threading.Thread(target=_check, daemon=True)
    t.start()
    t.join(_UNC_PROBE_TIMEOUT)
    return result[0]


def check_path_entry(entry: str) -> bool:
    """单条路径是否有效（用于提示/标红，不阻止保存）。

    - 先剥引号、展开 %VAR% 引用再判定存在性；
    - 裸盘符（如 "C:"）视为无效；
    - 展开后仍含未定义的 "%...%" 引用则无法判定，视为有效；
    - UNC 网络路径带超时探测。
    """
    e = entry.strip().strip('"').strip()
    if not e:
        return False
    if len(e) == 2 and e[1] == ":":
        return False
    expanded = os.path.expandvars(e)
    if "%" in expanded:
        return True
    if expanded.startswith("\\\\"):
        return _probe_exists(expanded)
    try:
        return os.path.exists(expanded)
    except Exception:
        return False


def validate_path_value(name: str, value: str) -> list[str]:
    """校验多路径变量值，返回无效条目列表（供提示，不阻止保存）

    PATHEXT 之类的非路径变量跳过检查；非 PATH 名称但值呈多路径形式
    的变量同样拆分检查（与原生工具行为一致）。
    """
    if name.strip().upper() == "PATHEXT":
        return []
    if not (is_path_var(name) or is_multi_path_value(value)):
        return []
    return [e for e in split_path_value(value) if not check_path_entry(e)]
