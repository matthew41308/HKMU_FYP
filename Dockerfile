# Use a slim Python base image
FROM python:3.9-slim

# Install Java (this installs the default Java Runtime Environment)
RUN apt-get update && \
    apt-get install -y default-jre && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the Python requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code into the container
COPY . .

# Create the directory for PlantUML jar and copy the jar file there
RUN mkdir -p /var/data/tools
COPY plantuml.jar /var/data/tools/plantuml.jar

# Expose the port your Flask app listens on (e.g., 5000)
EXPOSE 5000

# Start the Flask app using Gunicorn.
# "wsgi:app" tells Gunicorn to look for the app instance in wsgi.py.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]