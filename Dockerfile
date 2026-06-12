FROM astral/uv:python3.14-trixie-slim

RUN groupadd -r groupfastapi && useradd -r -g groupfastapi -m userfastapi
RUN chown -R userfastapi:groupfastapi /home/userfastapi

WORKDIR /app

COPY pyproject.toml uv.lock ./
ENV UV_NO_DEV=1
RUN uv sync --locked

COPY . .
EXPOSE 8000
USER userfastapi
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
