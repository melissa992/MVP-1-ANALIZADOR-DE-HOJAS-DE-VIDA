import os
import uuid
from typing import List
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="CV-Match AI - API",
    description="Sistema Inteligente de Extracción, Clasificación y Screening de Hojas de Vida",
    version="0.1.0"
)

# Habilitar CORS para permitir peticiones desde el Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En desarrollo permite cualquier origen
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "temp_storage"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/")
def read_root():
    return {"message": "Bienvenido a la API de CV-Match AI"}

@app.post("/upload-cv/")
async def upload_cvs(files: List[UploadFile] = File(...)):
    if len(files) > 20:
        raise HTTPException(
            status_code=400,
            detail="Se permite un máximo de 20 archivos PDF por carga."
        )
    
    uploaded_results = []
    
    for file in files:
        # 1. Validar extensión
        if not file.filename.lower().endswith(".pdf"):
            uploaded_results.append({
                "filename": file.filename,
                "status": "error",
                "message": "El archivo debe estar en formato PDF."
            })
            continue
        
        # 2. Validar firma binaria (%PDF)
        contents = await file.read()
        if not contents.startswith(b"%PDF"):
            uploaded_results.append({
                "filename": file.filename,
                "status": "error",
                "message": "El archivo no es un PDF válido o está corrupto."
            })
            continue
        
        # 3. Validar tamaño (10 MB máximo)
        if len(contents) > 10 * 1024 * 1024:
            uploaded_results.append({
                "filename": file.filename,
                "status": "error",
                "message": "El archivo excede el tamaño máximo de 10 MB."
            })
            continue
        
        # 4. Guardar archivo con identificador único
        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")
        with open(file_path, "wb") as f:
            f.write(contents)
            
        uploaded_results.append({
            "file_id": file_id,
            "filename": file.filename,
            "status": "success",
            "message": "Archivo cargado y almacenado correctamente."
        })
        
    return {
        "total_processed": len(files),
        "results": uploaded_results
    }