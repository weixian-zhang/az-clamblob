# Use an official Python runtime as a parent image
FROM python:3.12-slim as builder

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the container
COPY . .

# Use a smaller base image for the final stage
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the installed packages from the builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app /app

# Make port 80 available to the world outside this container
#EXPOSE 80

# Run the application
CMD ["python", "main.py"]

