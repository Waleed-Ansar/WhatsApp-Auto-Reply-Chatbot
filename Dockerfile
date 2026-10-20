FROM python:3.12-slim

WORKDIR /app

# Prevent Python buffering
ENV PYTHONUNBUFFERED=1

# ------------------------------------------------------------
# Install Microsoft ODBC Driver 18 for SQL Server
# ------------------------------------------------------------

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        gnupg \
        unixodbc \
        unixodbc-dev \
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc \
        | gpg --dearmor \
        -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
        > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
        msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# Python dependencies
# ------------------------------------------------------------

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------
# Application
# ------------------------------------------------------------

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]