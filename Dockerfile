FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Run both bot and webhook server
CMD ["./start.sh"]
