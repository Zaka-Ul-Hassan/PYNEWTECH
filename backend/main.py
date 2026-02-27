# backend\main.py

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from app.routes.linkedin import linkedin_auth_route
from app.schemas.response_schema import ResponseSchema


app = FastAPI()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ResponseSchema(
            Status=False,
            Message="Something went wrong.",
            Data=None
        ).dict()
    )

app.include_router(linkedin_auth_route.router,prefix="/auth/linkedin",tags=["LinkedIn Auth"])




if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)