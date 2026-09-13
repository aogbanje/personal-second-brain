# personal-second-brain
An advanced, AI-powered Personal Second Brain built with local document ingestion (PDFs/URLs), Chroma vector embeddings, dynamic semantic search, and structured JSON schema extraction.

# program structure
personal-second-brain/
│
├── config.py         # Loads and validates environment variables
├── database.py       # Manages localized Chroma DB setup
├── llm.py            # Manages API & local LLM routing logic
├── ingestion.py      # Parses and chunks documents (PDFs/URLs)
└── main.py           # The main entry point orchestrating everything
