from fastapi import FastAPI

from routes.agents import router as agents_router
from routes.agent_ws import router as agent_ws_router
from routes.docs import register_docs_routes
from routes.llm_info import router as llm_info_router
from routes.rag import router as rag_router
from routes.structured import router as structured_router
from auth.routes import router as auth_router
from users.routes import router as users_router
from credits.routes import router as credits_router
from shares.routes import router as shares_router
from routes.skills import router as skills_router
from routes.capsules import router as capsules_router


def register_routes(app: FastAPI) -> None:
    app.include_router(auth_router)
    app.include_router(agents_router)
    app.include_router(agent_ws_router)
    app.include_router(rag_router)
    app.include_router(llm_info_router)
    app.include_router(structured_router)
    app.include_router(users_router)
    app.include_router(credits_router)
    app.include_router(shares_router)
    app.include_router(skills_router)
    app.include_router(capsules_router)
    register_docs_routes(app)
