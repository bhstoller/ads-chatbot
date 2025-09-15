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

# Expose Streamlit port
EXPOSE 8080

# Run Streamlit when the container starts
CMD ["streamlit", "run", "/app/src/app/streamlit_app.py", "--server.port=8080", "--server.address=0.0.0.0"]