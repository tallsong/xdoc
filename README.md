```bash

pip install chromadb pinecone sentence-transformers
```



# usage


```bash
cd /home/azureuser/xdoc/backend && python -m app.vector_store.example

cd /home/azureuser/xdoc/backend && python examples/document_management_example.py

cd /home/azureuser/xdoc/backend && python examples/document_search_demo.py weekly

cd /home/azureuser/xdoc/backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

