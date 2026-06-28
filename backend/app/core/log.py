"""
企业级轻量日志：loguru + stdlib 接管
- 控制台（开发友好，带颜色）
- 文件（按大小 rotation + 压缩 + 保留天数）
- JSON 开关（接观测栈时打开）
- 接管 stdlib logging（langchain/langgraph/httpx 都走这个）

v2.0 调整：原样搬自 v1.0。
"""

import logging
import sys
from pathlib import Path

from loguru import logger


class InterceptHandler(logging.Handler):
    """把 stdlib logging 的记录重定向到 loguru"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_back and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging(
    level: str = "INFO",
    json_output: bool = False,
    log_dir: str = "logs",
    log_file_name: str = "app.log",
    rotation: str = "100 MB",
    retention: str = "30 days",
    compression: str = "zip",
    enqueue: bool = True,
    backtrace: bool = True,
    diagnose: bool = False,
) -> None:
    """
    初始化日志系统。在 main.py 第一行调用一次。

    Args:
        level: 全局最低级别 (TRACE/DEBUG/INFO/WARNING/ERROR)
        json_output: True 时输出 JSON（对接 Loki/ELK 用）
        log_dir: 日志文件目录
        log_file_name: 主日志文件名
        rotation: 切割触发条件（"100 MB" / "00:00" / "1 week"）
        retention: 保留时长（"30 days" / "10 files"）
        compression: 压缩格式（None / "zip" / "tar.gz"）
        enqueue: True 时多进程/异步安全（用 QueueHandler）
        backtrace: 异常时显示完整变量链
        diagnose: 异常时显示变量值（生产建议 False，避免泄漏敏感信息）
    """

    logger.remove()

    if json_output:
        logger.add(
            sys.stdout,
            level=level,
            serialize=True,
            enqueue=enqueue,
            backtrace=backtrace,
            diagnose=diagnose,
        )
    else:
        logger.add(
            sys.stdout,
            level=level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            enqueue=enqueue,
            backtrace=backtrace,
            diagnose=diagnose,
            colorize=True,
        )

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_path / log_file_name,
        level=level,
        rotation=rotation,
        retention=retention,
        compression=compression,
        encoding="utf-8",
        enqueue=enqueue,
        backtrace=backtrace,
        diagnose=diagnose,
        serialize=json_output,
    )

    logger.add(
        log_path / "error.log",
        level="ERROR",
        rotation=rotation,
        retention=retention,
        compression=compression,
        encoding="utf-8",
        enqueue=enqueue,
        backtrace=backtrace,
        diagnose=diagnose,
        serialize=json_output,
    )

    logging.root.handlers = [InterceptHandler()]
    logging.root.setLevel(level)

    for noisy in ("httpx", "httpcore", "urllib3", "openai", "langchain_community"):
        logging.getLogger(noisy).setLevel("WARNING")

    logger.info("logging initialized: level={}, json={}, dir={}", level, json_output, log_dir)


__all__ = ["logger", "setup_logging", "InterceptHandler"]
