# app/Dockerfile

FROM python:3.11-slim

EXPOSE 8501
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
CMD streamlit run Home.py \
    --server.headless true \
    --browser.serverAddress=0.0.0.0 \
    --server.enableCORS false \
    --browser.gatherUsageStats false