import os
import aiofiles
import csv
import textract
from typing import List
from fastapi import UploadFile, HTTPException
from docx import Document
from openpyxl import load_workbook  # ✅ Import for XLSX processing
from utils import extract_text_from_pdf
from supabase import create_client, Client  # ✅ Import Supabase

# Supabase Configuration
SUPABASE_URL = "https://your-supabase-project-url.supabase.co"  # Replace with your Supabase project URL
SUPABASE_KEY = "your-supabase-api-key"  # Replace with your Supabase service role key
SUPABASE_BUCKET = "uploads"  # Replace with your bucket name

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

UPLOAD_FOLDER = "/tmp/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


async def upload_files(files: List[UploadFile]) -> dict:
    """
    Upload and extract text from multiple file types:
    - PDF, TXT, DOC, DOCX, PAGES, RTF, MD, CSV, and XLSX.
    """
    combined_text = ""
    uploaded_files = []

    for file in files:
        try:
            file_extension = file.filename.split(".")[-1].lower()
            file_path = f"uploads/{file.filename}"  # Storage path in Supabase

            # ✅ Upload file to Supabase
            file_content = await file.read()  # Read file content
            response = supabase.storage.from_(SUPABASE_BUCKET).upload(file_path, file_content, file_options={"contentType": file.content_type})

            if "error" in response:
                raise HTTPException(status_code=500, detail=f"Failed to upload {file.filename} to Supabase: {response['error']}")

            # ✅ Get the public URL
            file_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{file_path}"
            uploaded_files.append({"filename": file.filename, "url": file_url})

            # ✅ Process text extraction (if needed)
            if file_extension == "pdf":
                pdf_text = extract_text_from_pdf(file_url)  # Modify this function to accept URLs if necessary
                combined_text += pdf_text + "\n"

            elif file_extension in ["txt", "md"]:
                combined_text += file_content.decode("utf-8") + "\n"

            elif file_extension == "docx":
                doc = Document(file_url)  # Modify text extraction to handle URLs
                combined_text += "\n".join([p.text for p in doc.paragraphs]) + "\n"

            elif file_extension in ["doc", "pages", "rtf"]:
                textract_text = textract.process(file_url).decode("utf-8")
                combined_text += textract_text + "\n"

            elif file_extension == "csv":
                csv_reader = csv.reader(file_content.decode("utf-8").splitlines())
                combined_text += "\n".join([", ".join(row) for row in csv_reader]) + "\n"

            elif file_extension == "xlsx":
                wb = load_workbook(file_url, data_only=True)  # Modify function to open from URLs
                for sheet in wb.sheetnames:
                    ws = wb[sheet]
                    for row in ws.iter_rows(values_only=True):
                        combined_text += ", ".join(str(cell) if cell else "" for cell in row) + "\n"

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error processing {file.filename}: {str(e)}")

    return {
        "message": f"Files uploaded successfully",
        "files": uploaded_files,
        "extracted_text": combined_text,
    }
