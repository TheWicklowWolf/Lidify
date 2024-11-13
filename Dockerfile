FROM python:3.12-alpine

# Set build arguments
ARG RELEASE_VERSION
ENV RELEASE_VERSION=${RELEASE_VERSION}

# Install su-exec
RUN apk update && apk add --no-cache su-exec

# Create directories and set permissions
COPY . /lidify
WORKDIR /lidify

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt

# Make the script executable
RUN chmod +x thewicklowwolf-init.sh

# Expose port
EXPOSE 5000

# Start the app
ENTRYPOINT ["./thewicklowwolf-init.sh"]
