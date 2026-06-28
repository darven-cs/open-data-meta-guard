"""MetaEvaluateWorker — 单 asyncio task 后台调度。

设计：
- lifespan 启动时 worker.start()，后台不停 tick
- 每个 tick：reset stale running → claim 一个 pending → spawn asyncio.create_task 跑评估
- 维护 self._running: dict[job_id, asyncio.Task] 用于 DELETE 取消
- 关闭：worker.stop() 取消所有 task + 等它们退出
"""
import asyncio

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.log import logger
from app.dao import meta_evaluation_job as job_dao


class MetaEvaluateWorker:
    """元数据评估作业后台调度器。"""

    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._running: dict[int, asyncio.Task] = {}
        self._stop = asyncio.Event()
        self._tick_sec = settings.meta_evaluate_worker_tick_sec
        self._stale_threshold = settings.meta_evaluate_stale_threshold_sec

    # ──────────────────────── lifecycle ────────────────────────

    async def start(self) -> None:
        """lifespan 启动期调用：兜底 reset stale + 创建后台 task。"""
        # 1) 兜底 reset stale running
        try:
            async with AsyncSessionLocal() as session:
                count = await job_dao.reset_stale_running(
                    session, stale_threshold_seconds=self._stale_threshold,
                )
                if count > 0:
                    logger.info(
                        "[meta-evaluate-worker] reset {} stale running job(s)",
                        count,
                    )
        except Exception as e:
            logger.warning(
                "[meta-evaluate-worker] reset_stale_running failed: {}", e,
            )

        logger.info(
            "[meta-evaluate-worker] started, tick={}s, timeout={}s, stale={}s",
            self._tick_sec,
            settings.meta_evaluate_timeout_sec,
            self._stale_threshold,
        )
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="meta-evaluate-worker")

    async def stop(self) -> None:
        """lifespan 关闭期调用：停止主循环 + 取消所有 running task。"""
        logger.info("[meta-evaluate-worker] stopping...")
        self._stop.set()

        # 取消所有 running 评估 task
        for job_id, t in list(self._running.items()):
            if not t.done():
                t.cancel()
                logger.info("[meta-evaluate-worker] cancelled job={}", job_id)

        # 等主循环退出
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("[meta-evaluate-worker] main loop did not stop in 10s")
                self._task.cancel()

        # 等所有 running 任务退出（带 timeout）
        if self._running:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._running.values(), return_exceptions=True),
                    timeout=10.0,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "[meta-evaluate-worker] some running tasks did not finish in 10s",
                )
            self._running.clear()

        logger.info("[meta-evaluate-worker] stopped")

    # ──────────────────────── public ────────────────────────

    async def cancel_job(self, job_id: int) -> bool:
        """取消运行中的 job。

        Returns:
            True = 取消信号已发；False = 找不到该 running job
        """
        task = self._running.get(job_id)
        if task is None or task.done():
            return False
        task.cancel()
        logger.info("[meta-evaluate-worker] cancel requested job={}", job_id)
        return True

    # ──────────────────────── 内部 ────────────────────────

    async def _run(self) -> None:
        """主循环：每 tick_sec 调度一次。"""
        while not self._stop.is_set():
            try:
                await self._tick()
            except Exception as e:
                logger.exception("[meta-evaluate-worker] tick error: {}", e)

            # 用 wait_for(_stop.wait()) 实现可中断 sleep
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self._tick_sec)
            except asyncio.TimeoutError:
                pass

    async def _tick(self) -> None:
        """一次 tick：claim 一个 pending → spawn task。"""
        # 清理已完成的 task 引用
        self._cleanup_finished()

        async with AsyncSessionLocal() as session:
            job = await job_dao.claim_next_pending(session)

        if job is None:
            return

        job_id = job["id"]
        dataset_id = job["dataset_id"]
        logger.info(
            "[meta-evaluate-worker] claimed job={} dataset_id={}",
            job_id, dataset_id,
        )

        # spawn 评估 task
        task = asyncio.create_task(
            self._run_evaluation(job_id, dataset_id),
            name=f"meta-evaluate-job-{job_id}",
        )
        self._running[job_id] = task

    def _cleanup_finished(self) -> None:
        finished = [jid for jid, t in self._running.items() if t.done()]
        for jid in finished:
            self._running.pop(jid, None)

    async def _run_evaluation(self, job_id: int, dataset_id: str) -> None:
        """实际执行一次评估；自动写终态。"""
        from app.service.meta_evaluate import evaluate_with_tracing

        try:
            result = await evaluate_with_tracing(
                dataset_id=dataset_id,
                job_id=job_id,
            )
            if not result.get("ok"):
                # service 层已自行写终态；这里只打 log
                logger.warning(
                    "[meta-evaluate-worker] job={} finished with error: {}",
                    job_id, result.get("error"),
                )
        except asyncio.CancelledError:
            # 兜底：万一 service 层没接住
            logger.info(
                "[meta-evaluate-worker] job={} cancelled (caught in worker)",
                job_id,
            )
            try:
                async with AsyncSessionLocal() as session:
                    await job_dao.mark_cancelled(
                        session, job_id, error="cancelled by user",
                    )
            except Exception:
                logger.exception(
                    "[meta-evaluate-worker] mark_cancelled failed for job={}", job_id,
                )
        except Exception as e:
            logger.exception(
                "[meta-evaluate-worker] job={} unexpected error: {}", job_id, e,
            )
            try:
                async with AsyncSessionLocal() as session:
                    await job_dao.mark_failed(
                        session, job_id, f"worker unexpected error: {e}",
                    )
            except Exception:
                logger.exception(
                    "[meta-evaluate-worker] mark_failed failed for job={}", job_id,
                )
        finally:
            self._running.pop(job_id, None)


# 模块级单例
worker = MetaEvaluateWorker()


__all__ = ["MetaEvaluateWorker", "worker"]