import asyncio
import os
import sys
from database import initialize_vector_db
from llm import query_second_brain
from ingestion import extract_and_chunk_pdf

async def main():
    print("🚀 Bootstrapping Modular Personal Second Brain...")
    
    # 1. Initialize the vector storage engine
    kb_collection = initialize_vector_db()
    if not kb_collection:
        print("🛑 Bootstrapping halted due to database initialization failure.")
        return
    
    # 2. Ingest and extract clean data chunks from your PDF document
    target_pdf = "./sample_data/my_document.pdf"
    
    if os.path.exists(target_pdf):
        pdf_chunks = extract_and_chunk_pdf(target_pdf)
        
        # 3. Convert text to math vectors and save inside Chroma DB if empty
        if pdf_chunks:
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

    # 4. Define our test query
    user_query = "What are the core steps to build a local RAG pipeline without orchestration frameworks?"
    print(f"\n🔍 Searching vector base for context matching: '{user_query}'...")
    
    # 5. Perform the mathematical semantic lookup 
    try:
        results = kb_collection.query(
            query_texts=[user_query],
            n_results=3
        )
        
        # Chroma returns a dictionary with a list of lists inside 'documents'
        retrieved_contexts = results.get('documents', [[]])[0]
        
        print(f"✅ Database Lookup Complete. Retrieved {len(retrieved_contexts)} relevant text blocks.")
        for idx, text in enumerate(retrieved_contexts):
            print(f"   [Context Block {idx+1} Preview]: {text[:80]}...")
            
        if not retrieved_contexts:
            print("🛑 Cannot execute query. The matching vector lookup returned zero contexts.")
            return

        # 6. Route the matching facts directly to xKiro reasoning engine
        print("🌐 Opening network channel to xKiro proxy gateway...")
        response = await query_second_brain(query=user_query, retrieved_contexts=retrieved_contexts)
        
        if not response:
            print("⚠️ The xKiro network channel returned an empty string or failed silently.")

    except Exception as e:
        print(f"❌ Error during terminal lifecycle pipeline execution: {e}", file=sys.stderr)

if __name__ == "__main__":
    asyncio.run(main())
