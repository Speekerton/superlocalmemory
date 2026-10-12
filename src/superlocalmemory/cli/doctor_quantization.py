"""Actionable, read-only QJL upgrade health for the active profile."""

from dataclasses import replace
from pathlib import Path

from superlocalmemory.core.config import SLMConfig
from superlocalmemory.storage.memory_write import memory_read
from superlocalmemory.storage.qjl_repair import repair_status


def qjl_finding(db_path: str | Path) -> tuple[str, str, str]:
    config = SLMConfig.load()
    quantization = replace(config.quantization, polar=replace(
        config.quantization.polar, dimension=config.embedding.dimension))
    with memory_read(db_path) as conn:
        status = repair_status(conn, config.active_profile, quantization)
    needed, missing = status["repair_needed"], status["unrecoverable"]
    detail = (f"{needed} need repair ({status['legacy']} legacy, "
              f"{status['incompatible']} incompatible); {missing} need re-embedding")
    fix = ("Run `slm quantize --execute` to repair from retained original vectors; "
           "re-embed memories without a usable original vector") if needed else ""
    return "WARN" if needed else "PASS", detail, fix
