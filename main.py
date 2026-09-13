import asyncio
import os
from database import initialize_vector_db
from llm import query_second_brain
from ingestion import extract_and_chunk_pdf

async def main():
    print("🚀 Bootstrapping Modular Personal Second Brain...")
    
    # 1. Initialize the vector storage engine with the OpenAI layer bound to it
    kb_collection = initialize_vector_db()
    if not kb_collection:
        print("🛑 Bootstrapping halted due to database initialization failure.")
        return
    
    # 2. Ingest and extract clean data chunks from your PDF document
    target_pdf = "./sample_data/my_document.pdf"
    
    if os.path.exists(target_pdf):
        pdf_chunks = extract_and_chunk_pdf(target_pdf)
        
        # 3. Convert text to math vectors and save inside Chroma DB if needed
        if pdf_chunks:
            # Let's check if we've already uploaded this document to save API costs
            existing_data = kb_collection.get(limit=1)
            if len(existing_data['ids']) == 0:
                print(f"⚡ Processing and vectorizing {len(pdf_chunks)} chunks...")
                doc_name = os.path.basename(target_pdf).replace(".pdf", "")
                chunk_ids = [f"id_{doc_name}_{i}" for i in range(len(pdf_chunks))]
                
                kb_collection.add(documents=pdf_chunks, ids=chunk_ids)
                print("💾 Vector chunks saved permanently to local disk storage.")
            else:
                print("💡 Database already populated with contextual knowledge data.")
    else:
        print(f"💡 Document not found at '{target_pdf}'. Operating purely on existing vector database storage.")

    # 4. Let the user query their Second Brain knowledge base interactively
    user_query = "What are the core steps to build a local RAG pipeline without orchestration frameworks?"
    print(f"\n🔍 Searching vector base for context matching: '{user_query}'...")
    
    # Perform a mathematical lookup for the top 3 most similar document chunks
    results = kb_collection.query(
        query_texts=[user_query],
        n_results=3
    )
    
    retrieved_texts = results.get('documents', [[]])[0]
    
    if retrieved_texts:
        # 5. Route the user query along with the isolated facts directly to OpenAI
        await query_second_brain(query=user_query, retrieved_contexts=retrieved_texts)
    else:
        print("🛑 Cannot execute query. The vector base is completely empty. Please drop a valid PDF in './sample_data/my_document.pdf' first.")

if __name__ == "__main__":
    asyncio.run(main())
