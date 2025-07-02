# Use official slim Python base
FROM python:3.10-slim

# Set environment variables
ENV ACCEPT_EULA=Y
ENV DEBIAN_FRONTEND=noninteractive

# Install required system tools and remove conflicting ODBC packages
RUN apt-get update && \
    apt-get install -y curl gnupg2 apt-transport-https unixodbc gcc g++ && \
    apt-get remove -y libodbc2 libodbcinst2 unixodbc-common && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy app files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose FastAPI port
EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
