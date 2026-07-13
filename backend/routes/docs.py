from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from starlette.responses import HTMLResponse

from docs_theme import (
    redoc_body_opening_replacement,
    redoc_head_inject,
    redoc_theme_html_attr,
    swagger_dark_head_inject,
)


def register_docs_routes(app: FastAPI) -> None:
    @app.get("/docs", include_in_schema=False)
    async def swagger_ui_docs():
        r = get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Swagger UI",
            swagger_ui_parameters={"syntaxHighlight.theme": "monokai"},
        )
        page = r.body.decode()
        page = page.replace("</head>", f"{swagger_dark_head_inject()}</head>", 1)
        return HTMLResponse(content=page, status_code=r.status_code)

    @app.get("/redoc", include_in_schema=False)
    async def redoc_docs():
        r = get_redoc_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - ReDoc",
            with_google_fonts=False,
        )
        page = r.body.decode()
        page = page.replace("</head>", f"{redoc_head_inject()}</head>", 1)
        theme = redoc_theme_html_attr()
        old = f'<redoc spec-url="{app.openapi_url}"></redoc>'
        new = f'<redoc spec-url="{app.openapi_url}" theme="{theme}"></redoc>'
        page = page.replace(old, new, 1)
        page = page.replace("body {", redoc_body_opening_replacement(), 1)
        return HTMLResponse(content=page, status_code=r.status_code)
