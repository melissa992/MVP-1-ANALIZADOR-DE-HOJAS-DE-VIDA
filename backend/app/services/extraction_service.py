import os
from uuid import UUID
import pdfplumber
from fastapi import HTTPException

UPLOAD_DIR = "temp_storage"


def get_pdf_path(file_id: str) -> str:
    try:
        normalized_file_id = str(UUID(file_id))
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail="El archivo especificado no existe o el identificador es incorrecto.",
        ) from error

    file_path = os.path.join(UPLOAD_DIR, f"{normalized_file_id}.pdf")
    # Validar si el archivo existe
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail="El archivo especificado no existe o el identificador es incorrecto."
        )

    return file_path


def extract_text_from_pdf_service(file_id: str) -> dict:
    file_path = get_pdf_path(file_id)
    extracted_text = ""
    pages_data = []

    try:
        with pdfplumber.open(file_path) as pdf:
            if len(pdf.pages) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="El archivo PDF está vacío o corrupto."
                )
            
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text(layout=False) or ""
                pages_data.append({
                    "page": page_num,
                    "text_length": len(text)
                })
                extracted_text += f"\n--- Página {page_num} ---\n" + text

        # Validar si el texto extraído es demasiado corto (posible PDF escaneado / imagen)
        if len(extracted_text.strip()) < 50:
            return {
                "status": "warning",
                "file_id": file_id,
                "message": "El PDF parece ser un documento escaneado (imagen). Se requerirá un flujo alternativo de OCR.",
                "extracted_text": "",
                "total_pages": len(pdf.pages)
            }

        return {
            "status": "success",
            "file_id": file_id,
            "total_pages": len(pdf.pages),
            "extracted_text": extracted_text.strip(),
            "pages_summary": pages_data
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el documento PDF: {str(e)}"
        )