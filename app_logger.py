# -*- coding: utf-8 -*-
"""
SDN Downloader Ultra - Advanced Logging & Diagnostics Module
يوفر تسجيل متقدم للأخطاء والأداء مع تنظيف تلقائي
"""
import os
import sys
import logging
import logging.handlers
import traceback
from datetime import datetime
from pathlib import Path

# --- Configuration ---
LOG_DIR = Path(os.path.expanduser("~")) / ".sdn_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "sdn_app.log"
LOG_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
LOG_BACKUP_COUNT = 3

# --- Advanced Logger Setup ---
def setup_logger(name: str = "SDN") -> logging.Logger:
    """تهيئة مسجل متقدم مع تدوير تلقائي للملفات"""
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    
    # Formatter with full diagnostic info
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(threadName)-14s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Rotating file handler
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
    # Console handler (stderr only for warnings+)
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    return logger


def log_exception(logger: logging.Logger, msg: str = "حدث خطأ غير متوقع"):
    """تسجيل استثناء مع تتبع كامل للمكدس"""
    exc_info = sys.exc_info()
    if exc_info and exc_info[0]:
        logger.error(f"{msg}: {exc_info[1]}", exc_info=True)
    else:
        logger.error(msg)


def get_diagnostic_info() -> dict:
    """تجميع معلومات تشخيصية كاملة عن النظام"""
    import platform
    return {
        "timestamp": datetime.now().isoformat(),
        "os": platform.platform(),
        "python_version": sys.version,
        "python_executable": sys.executable,
        "frozen": getattr(sys, 'frozen', False),
        "cpu_count": os.cpu_count(),
        "cwd": os.getcwd(),
        "log_file": str(LOG_FILE),
    }


def cleanup_old_logs():
    """حذف ملفات السجل القديمة جداً (أكثر من 30 يوم)"""
    try:
        now = datetime.now().timestamp()
        for f in LOG_DIR.glob("sdn_app.log*"):
            if now - f.stat().st_mtime > 30 * 86400:
                f.unlink(missing_ok=True)
    except Exception:
        pass
