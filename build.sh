#!/bin/bash

# Exit on any error
set -e

# Install system packages for ODBC Driver 17
apt-get update && apt-get install -y curl gnupg2 apt-transport-https

curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list

apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev

# Check installation
echo "✅ ODBC Driver installed:"
odbcinst -q -d -n "ODBC Driver 17 for SQL Server" || echo "❌ Driver still not available"

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
