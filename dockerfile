# Use Python 3.11 as the base image (adjust version if needed)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy the application code
COPY server_math.py /app/

# Install required dependencies
# Assuming mcp libraries and pydantic are pip-installable
RUN pip install --no-cache-dir pydantic mcp-server uvx mcpo

# Expose the port the app will run on
EXPOSE 8000

# Set environment variables (if needed)
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD ["uvx", "mcpo", "--port", "8000", "--api-key", "top-secret", "--", "uv", "run", "server_math.py"]