import os
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def extract_and_chunk_pdf(pdf_path: str, chunk_size: int = 500, chunk_overlap: int = 50):
    """
    Reads a local PDF, extracts raw text content, and splits it into 
    semantic, overlapping text windows optimized for Vector database indexing.
    """
    if not os.path.exists(pdf_path):
        print(f"❌ Target document not found at: {pdf_path}")
        return []
        
    print(f"📄 Ingesting document: {os.path.basename(pdf_path)}...")
    
    # 1. Read the PDF content page by page
    reader = PdfReader(pdf_path)
    raw_text = ""
    for page_num, page in enumerate(reader.pages):
        page_content = page.extract_text()
        if page_content:
            raw_text += page_content + "\n"
            
    print(f"✨ Extracted {len(raw_text)} raw characters.")

    # 2. Split text using LangChain's production standard chunker
    # It splits by paragraphs (\n\n), sentences (\n), and words (" ") to keep ideas together.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )
    
    chunks = text_splitter.split_text(raw_text)
    print(f"🧩 Successfully split document into {len(chunks)} text chunks.")
    
    # Preview the first chunk
    if chunks:
        print(f"💡 Sample Chunk 1:\n--- \n{chunks[0]}\n---")
        
    return chunks

if __name__ == "__main__":
    # Quick standalone test: create an empty test folder
    os.makedirs("./sample_data", exist_ok=True)
    print("📁 Put a sample PDF inside the './sample_data' folder to test ingestion!")
    
    # Example execution line (uncomment when you have a PDF ready):
    # extract_and_chunk_pdf("./sample_data/my_document.pdf")
