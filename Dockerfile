# Use a lightweight Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY src/app/requirements.txt ./requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create folder for your vector store (if needed)
RUN mkdir -p /app/data/chroma_rag_store

# Expose the port Cloud Run expects
EXPOSE 8080

# --- Cloud Run / Streamlit fixes ---
# Disable file watching (prevents "Connecting…/Running…" loop)
# Disable usage stats prompts
ENV STREAMLIT_SERVER_FILE_WATCHER_TYPE=none \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    PORT=8080

# Run Streamlit with Cloud Run’s PORT
CMD ["streamlit", "run", "src/app/streamlit_app.py", \
     "--server.port=8080", \
     "--server.address=0.0.0.0", \
     "--server.enableCORS=false", \
     "--server.enableXsrfProtection=false"]
