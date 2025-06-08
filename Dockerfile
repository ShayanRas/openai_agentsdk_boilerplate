# Use an official Python runtime as a parent image
FROM python:3.7-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies that might be needed (if any)
# RUN apt-get update && apt-get install -y --no-install-recommends some-package && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Make the start script executable
# We will create start.sh in the next step
RUN chmod +x ./start.sh

# Expose ports for the MCP server and the FastAPI app
EXPOSE 8000
EXPOSE 8001

# The command to run when the container starts
# We will define start.sh to run both test_mcp_server.py and uvicorn
# For now, let's set a placeholder CMD or an initial CMD for uvicorn, 
# and we'll refine this with start.sh
# CMD ["./start.sh"]
CMD ["./start.sh"]
