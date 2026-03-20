from fastapi import FastAPI

app = FastAPI()

@app.use("/")
async def greet():
    return {"greet": "hello world"}