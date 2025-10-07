# Use official Python image as base
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy the project into the image
ADD . /app

# Sync the project into a new environment, asserting the lockfile is up to date
RUN uv sync --locked --no-dev

EXPOSE 3000

ENV TRANSPORT=streamable-http
ENV LOG_LEVEL=INFO
ENV HOST=0.0.0.0
ENV PORT=3000
ENV MODEL=imagen-4.0-generate-001
ENV GEMINI_API_KEY="fake-key"

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

CMD ["run-server"]
VOLUME /data
