"""备份持久化：全量快照、自动备份（节流/去重/上限）、恢复、导入导出。"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from datetime import datetime
from pathlib import Path

import winreg

from core import registry, settings_store
from core.registry import SCOPE_SYSTEM, SCOPE_USER, Var

# 自动备份节流间隔（秒）：窗口内的连续变更只做一次自动备份，降低落盘频率。
# 内容去重（content_hash）不受节流影响；恢复前的 pre_restore 快照用 force 跳过节流。
_AUTO_BACKUP_MIN_INTERVAL = 60.0

# 自动备份保留上限：超出后从最旧开始清理，防止备份目录无限膨胀
_MAX_AUTO_BACKUPS = 5

_auto_backup_lock = threading.Lock()
_last_auto_backup_at = 0.0


def _slug(text: str) -> str:
    """把描述压成可安全用于文件名的短串。"""
    s = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in text)
    return s.strip("_")[:40]


def _backup_payload(vars_: list[Var], description: str = "", content_hash: str = "") -> dict:
    data = {
        "app": "变量管理器",
        "version": 1,
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "description": description,
        "vars": [v.to_dict() for v in vars_],
    }
    if content_hash:
        data["content_hash"] = content_hash
    return data


def _snapshot_hash(vars_: list[Var]) -> str:
    """全量快照的内容摘要，用于跳过内容相同的自动备份。"""
    # \x1f 单元分隔符不会出现在合法的注册表字符串里，避免字段拼接歧义
    payload = "\x1e".join(
        "\x1f".join((v.scope, v.name, str(v.kind), v.value)) for v in vars_
    )
    return hashlib.sha1(payload.encode("utf-8", "surrogatepass")).hexdigest()


def snapshot_vars() -> list[Var]:
    """当前用户 + 系统全部字符串环境变量的快照。"""
    out = registry.list_vars(SCOPE_USER)
    try:
        out += registry.list_vars(SCOPE_SYSTEM)
    except RuntimeError:
        pass  # 无管理员权限时仅快照用户变量
    return out


def auto_backup(description: str = "", force: bool = False) -> Path | None:
    """变更后自动备份：把当前全量状态快照存入备份目录。

    节流：间隔小于 _AUTO_BACKUP_MIN_INTERVAL 的连续变更只做一次（force=True 跳过，
    供 pre_restore 等必须留档的场景）；去重：内容与最近一份自动备份一致时不写新文件；
    上限：auto_ 前缀的备份最多保留 _MAX_AUTO_BACKUPS 份，防止目录膨胀。
    失败静默（不影响主流程）。返回备份文件路径或 None。
    """
    global _last_auto_backup_at
    with _auto_backup_lock:
        now = time.monotonic()
        if not force and now - _last_auto_backup_at < _AUTO_BACKUP_MIN_INTERVAL:
            return None
        _last_auto_backup_at = now
    try:
        settings_store.ensure_dirs()
        vars_ = snapshot_vars()
        digest = _snapshot_hash(vars_)

        # 内容与最近一份自动备份一致则跳过，避免重复文件
        recent = _auto_backup_files()
        if recent:
            try:
                data = json.loads(recent[0].read_text("utf-8"))
                if isinstance(data, dict) and data.get("content_hash") == digest:
                    _prune_auto_backups()
                    return recent[0]
            except (OSError, ValueError):
                pass

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = _slug(description)
        fname = f"auto_{slug}_{stamp}.json" if slug else f"auto_{stamp}.json"
        path = settings_store.BACKUPS_DIR / fname
        if path.exists():  # 同秒兜底，避免覆盖
            path = (
                settings_store.BACKUPS_DIR
                / f"auto_{slug or 'backup'}_{int(time.time() * 1000)}.json"
            )
        write_backup_raw(path, _backup_payload(vars_, description, digest), compact=True)
        _prune_auto_backups()
        return path
    except Exception:
        return None


def _auto_backup_files() -> list[Path]:
    """按修改时间倒序返回全部 auto_ 备份文件。"""
    try:
        files = [p for p in settings_store.BACKUPS_DIR.glob("auto_*.json") if p.is_file()]
    except OSError:
        return []
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def _prune_auto_backups() -> None:
    """自动备份超出上限时从最旧开始删除（只清理 auto_ 前缀）。"""
    for p in _auto_backup_files()[_MAX_AUTO_BACKUPS:]:
        try:
            p.unlink()
        except OSError:
            pass


def create_backup(description: str = "") -> Path:
    """手动创建备份：全量快照 + 描述，不受自动备份上限约束。"""
    settings_store.ensure_dirs()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = _slug(description)
    fname = f"backup_{slug}_{stamp}.json" if slug else f"backup_{stamp}.json"
    path = settings_store.BACKUPS_DIR / fname
    if path.exists():
        path = (
            settings_store.BACKUPS_DIR
            / f"backup_{slug or 'manual'}_{int(time.time() * 1000)}.json"
        )
    vars_ = snapshot_vars()
    write_backup_raw(path, _backup_payload(vars_, description, _snapshot_hash(vars_)))
    return path


def restore_backup(path: Path) -> list[str]:
    """恢复备份文件：先自动备份当前状态（pre_restore），再逐条写回。

    返回恢复失败的变量名列表（如系统变量缺管理员权限）。
    """
    vars_ = load_backup(Path(path))
    auto_backup("pre_restore", force=True)
    failed: list[str] = []
    for v in vars_:
        try:
            registry._set_raw(v.scope, v.name, v.value, v.kind)
        except (RuntimeError, OSError):
            failed.append(f"{'系统' if v.scope == SCOPE_SYSTEM else '用户'}：{v.name}")
    registry.broadcast_change()
    return failed


def export_backup(path: Path, vars_: list[Var], description: str = "") -> None:
    """把变量列表写为备份 JSON 文件。"""
    write_backup_raw(Path(path), _backup_payload(vars_, description))


def write_backup_raw(path: Path, data: dict, compact: bool = False) -> None:
    """写备份 JSON。compact=True 用于自动备份（体积约省 40%），导出保持缩进可读。"""
    settings_store.ensure_dirs()
    if compact:
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    else:
        text = json.dumps(data, ensure_ascii=False, indent=2)
    Path(path).write_text(text, "utf-8")


def read_backup_raw(path: Path) -> dict:
    """读取并校验备份文件，返回原始 dict；格式不正确时抛 ValueError。"""
    data = json.loads(Path(path).read_text("utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("vars"), list):
        raise ValueError("备份文件格式不正确")
    return data


def load_backup(path: Path) -> list[Var]:
    """把备份文件解析为 Var 列表，自动跳过非法条目。"""
    data = read_backup_raw(path)
    out: list[Var] = []
    for item in data["vars"]:
        if not isinstance(item, dict):
            continue
        scope = item.get("scope")
        name = item.get("name")
        value = item.get("value")
        kind = item.get("kind")
        if scope not in (SCOPE_USER, SCOPE_SYSTEM):
            continue
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(value, str):
            continue
        if kind not in (winreg.REG_SZ, winreg.REG_EXPAND_SZ):
            kind = winreg.REG_SZ
        out.append(Var(scope, name, value, kind))
    return out


def list_backups() -> list[dict]:
    """列出备份目录中的 JSON 备份，按时间倒序，跳过无法读取的文件。

    每项包含 path / name / mtime / count / description。
    """
    settings_store.ensure_dirs()
    items: list[dict] = []
    for p in settings_store.BACKUPS_DIR.glob("*.json"):
        try:
            stat = p.stat()
        except OSError:
            continue
        count = None
        description = ""
        try:
            data = read_backup_raw(p)
            count = len(data["vars"])
            description = str(data.get("description") or "")
        except (OSError, ValueError):
            pass  # 损坏文件仍列出，标记未知大小
        items.append(
            {
                "path": p,
                "name": p.name,
                "mtime": stat.st_mtime,
                "count": count,
                "description": description,
            }
        )
    items.sort(key=lambda it: it["mtime"], reverse=True)
    return items


def delete_backup(path: Path) -> None:
    Path(path).unlink(missing_ok=True)
