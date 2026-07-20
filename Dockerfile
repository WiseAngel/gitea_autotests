FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy AS base
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir uv && uv pip install --system .
COPY . .
RUN useradd -m qa && chown -R qa:qa /app
USER qa
CMD ["pytest", "--browser=chromium", "--alluredir=allure-results", "-v"]