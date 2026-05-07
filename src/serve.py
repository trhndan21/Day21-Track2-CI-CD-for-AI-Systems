from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.cloud import storage
import joblib
import os

app = FastAPI()

# Đọc tên bucket từ biến môi trường
GCS_BUCKET = os.environ.get("GCS_BUCKET", "your-bucket-name")
GCS_MODEL_KEY = "models/latest/model.pkl"
MODEL_PATH = os.path.expanduser("~/models/model.pkl")

def download_model():
    """Tải file model.pkl từ GCS về máy khi server khởi động."""
    if not os.path.exists(os.path.dirname(MODEL_PATH)):
        os.makedirs(os.path.dirname(MODEL_PATH))
    
    try:
        client = storage.Client()
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(GCS_MODEL_KEY)
        blob.download_to_filename(MODEL_PATH)
        print(f"Downloaded model from gs://{GCS_BUCKET}/{GCS_MODEL_KEY} to {MODEL_PATH}")
    except Exception as e:
        print(f"Error downloading model: {e}")
        # For local testing if GCS fails, we assume model.pkl might be in models/
        if os.path.exists("models/model.pkl") and not os.path.exists(MODEL_PATH):
            import shutil
            shutil.copy("models/model.pkl", MODEL_PATH)
            print("Using local models/model.pkl as fallback")

# Gọi hàm này khi module được import
if os.environ.get("SKIP_MODEL_DOWNLOAD") != "1":
    download_model()

if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)
else:
    model = None

class PredictRequest(BaseModel):
    features: list[float]

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/predict")
def predict(req: PredictRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if len(req.features) != 12:
        raise HTTPException(status_code=400, detail="Expected 12 features (wine quality)")
    
    prediction = int(model.predict([req.features])[0])
    labels = {0: "thấp", 1: "trung bình", 2: "cao"}
    
    return {
        "prediction": prediction,
        "label": labels.get(prediction, "unknown")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
