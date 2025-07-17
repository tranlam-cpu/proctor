FROM python:3.10.11-slim

WORKDIR /app

# Copy requirements từ root và install
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy toàn bộ project
COPY . .

# Set permissions
RUN chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]