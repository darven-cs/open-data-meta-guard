"""
FastAPI 应用工厂。

v2.0 调整：
  - **Phase 0 只注册 health router**
  - **Phase 1 注册 meta_collect router**（datasets 采集）
  - Phase 2-5 依次加入 meta_evaluate / data_collect /
    data_quality / chat router
  - 移除 v1.0 的 agent / meta_collect router
"""
from dotenv import load_dotenv

# load_dotenv() 必须在 import app.api.routes 之前
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.log import setup_logging, logger
from app.core.lifespan import app_lifespan

from app.api.routes import health
from app.api.routes import meta_collect  # Phase 1


def create_app():
    setup_logging()

    # lifespan 接管 PG 连接生命周期（详见 app/core/lifespan.py）
    app = FastAPI(lifespan=app_lifespan)

    # 全局异常拦截
    @app.exception_handler(Exception)
    async def _global_exception_handler(request: Request, exc: Exception):
        logger.exception("unhandled exception")
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error"},
        )

    # Phase 0: health
    app.include_router(health.router)
    # Phase 1: meta_collect
    app.include_router(meta_collect.router)
    return app
