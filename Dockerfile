FROM python:3.10-alpine

# Create a user and working directory
RUN adduser -D -u 1000 -g 1000 -s /bin/sh app
USER app
WORKDIR /home/app

# Install dependencies
COPY --chown=app:app requirements.txt .
RUN pip3 install --disable-pip-version-check --no-cache-dir --no-warn-script-location -r requirements.txt

# Copy source code
COPY --chown=app:app . .

# Run app entrypoint
CMD ["python3", "start.py"]
