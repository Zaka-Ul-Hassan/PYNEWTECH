# backend\main.py

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware 
import uvicorn

from app.schemas.response_schema import ResponseSchema
from app.routes.linkedin import linkedin_auth_route
from app.routes.zoom import zoom_route


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ResponseSchema(
            status=False,
            message="Something went wrong.",
            data=None
        ).dict()
    )


app.include_router(linkedin_auth_route.router,prefix="/auth/linkedin",tags=["LinkedIn Auth"])
app.include_router(zoom_route.router,prefix="/zoom",tags=["Zoom"])



if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)