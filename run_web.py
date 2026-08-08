import uvicorn


if __name__ == "__main__":
    uvicorn.run("backend.main_web:app", host="127.0.0.1", port=8100, reload=True)

