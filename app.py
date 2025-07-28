from fastapi import FastAPI
from controler.prediction import router as prediction_router
from controler.stats import router as stats_router
from controler.image import router as images_router
from controler.labels import router as labels_router
from controler.health import router as health_router

app = FastAPI()
app.include_router(prediction_router)
app.include_router(stats_router)
app.include_router(images_router)
app.include_router(labels_router)
app.include_router(health_router)

if __name__ == "__main__": # pragma: no cover
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)  # pragma: no cover
