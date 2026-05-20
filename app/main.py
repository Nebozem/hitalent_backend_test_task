from fastapi import FastAPI

app = FastAPI(title="hitalent_test")

@app.get("/")
def root():
    return {"message": "API is working"}