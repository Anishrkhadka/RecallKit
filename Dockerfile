FROM python:3.11-slim


# Install Python deps
RUN pip install --no-cache-dir streamlit

WORKDIR /app

# Copy source code
COPY streamlit_app.py /src/utils.py /app/

# Copy static assets (HTML, CSS, JS, etc.)
COPY static /app/static

# Ensure build dir exists at runtime
RUN mkdir -p /app/web/build

EXPOSE 8501

# Launch Streamlit
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
