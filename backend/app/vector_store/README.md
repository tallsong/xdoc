# Help document for running Pinecone example

"""
Pinecone Vector Store Example
============================

This example demonstrates using the Pinecone vector store adapter.
Before running, you'll need:

1. A Pinecone account and API key
2. Python packages installed:
   pip install pinecone-client==3.0.0 sentence-transformers

3. Set environment variables:
   export PINECONE_API_KEY=your-key-here
   export PINECONE_ENV=gcp-starter    # Or your chosen region like us-west1-gcp
   export PINECONE_INDEX=your-index   # Optional, defaults to 'example-index'

Common Pinecone Environments:
- gcp-starter (Free tier)
- us-west1-gcp
- us-east1-gcp
- eu-west1-gcp
- ap-southeast-1-gcp

Run the example:
python -m app.vector_store.example_pinecone
"""