FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY ./PromptingCode/requirements.txt /app/PromptingCode/requirements.txt
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r /app/PromptingCode/requirements.txt

# Copy the application code into the container
COPY . /app

# Define a volume for persistent data storage (can also be mapped to a local directory)
VOLUME ["/app/PromptingCode/Results"]

# Expose port 8000
EXPOSE 8000

# Define the command to run the application
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
