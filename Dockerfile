FROM python:3.11-slim

# Install deps
RUN pip install streamlit

WORKDIR /app
COPY streamlit_app.py parser.py /app/

# ensure build dir exists at runtime
RUN mkdir -p /app/web/build

EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
