# from fastapi import FastAPI, UploadFile, File,APIRouter
# from pydantic import BaseModel
# import faiss, os
# from sentence_transformers import SentenceTransformer
# from PyPDF2 import PdfReader
# import docx

# pma = APIRouter(prefix="/pma", tags=["PMA"])


# # Load embedding model
# model = SentenceTransformer("all-MiniLM-L6-v2")

# # Create FAISS index (768 = embedding size of MiniLM)
# index = faiss.IndexFlatL2(384)
# documents = []  # store metadata alongside embeddings

# # --- Utils ---
# def extract_text(file: UploadFile):
#     text = ""
#     if file.filename.endswith(".pdf"):
#         reader = PdfReader(file.file)
#         for page in reader.pages:
#             text += page.extract_text() + "\n"
#     elif file.filename.endswith(".docx"):
#         doc = docx.Document(file.file)
#         for para in doc.paragraphs:
#             text += para.text + "\n"
#     else:  # fallback
#         text = file.file.read().decode("utf-8")
#     return text

# def chunk_text(text, max_chars=500):
#     return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

# # --- Routes ---
# @pma.post("/upload-doc")
# async def upload_doc(file: UploadFile = File(...)):
#     text = extract_text(file)
#     chunks = chunk_text(text)

#     embeddings = model.encode(chunks)
#     index.add(embeddings)

#     # Save metadata
#     for chunk in chunks:
#         documents.append({"text": chunk, "filename": file.filename})

#     return {"msg": f"Uploaded {file.filename}", "chunks": len(chunks)}

# class Query(BaseModel):
#     question: str

# @app.post("/query-doc")
# async def query_doc(q: Query):
#     if index.ntotal == 0:
#         return {"error": "No documents indexed yet. Please upload a document first."}

#     q_embedding = model.encode([q.question])
#     D, I = index.search(q_embedding, k=3)

#     if len(I[0]) == 0:
#         return {"error": "No results found in index."}

#     context = "\n".join([documents[i]["text"] for i in I[0]])

#     prompt = f"Use the following context to answer the question.\n\nContext:\n{context}\n\nQuestion: {q.question}"

#     try:
#         res = requests.post(
#             "http://127.0.0.1:11434/api/generate",
#             json={"model": "llama3", "prompt": prompt}
#         )
#         res.raise_for_status()
#         answer = res.json()["response"]
#     except Exception as e:
#         answer = f"❌ Error calling Ollama API: {e}"

#     return {"question": q.question, "context_used": context, "answer": answer}