# Use the official ESI OpenFOAM development image
FROM opencfd/openfoam-default:2312

# Run as root to install system packages
USER root

# Install Python 3 and numerical/plotting libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-numpy \
    python3-matplotlib \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container
WORKDIR /app

# Copy all project files into the container
COPY . /app

# Ensure scripts are executable
RUN chmod +x /app/generate_geometry.py /app/run_sweep.py

# Create the output volume mount directory
RUN mkdir -p /app/output && chmod 777 /app/output

# Set the default entrypoint to run the python sweep script
ENTRYPOINT ["python3", "/app/run_sweep.py"]
