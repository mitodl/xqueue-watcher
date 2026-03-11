FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

RUN apt-get update && \
    apt-get install -y --no-install-recommends git-core && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m --shell /bin/false app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /edx/app/xqueue_watcher

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . /edx/app/xqueue_watcher
RUN uv sync --frozen --no-dev

USER app

CMD ["xqueue-watcher", "-d", "/edx/etc/xqueue_watcher"]

FROM base AS edx.org
USER root
RUN uv sync --frozen --extra production
USER app
CMD ["newrelic-admin", "run-program", "xqueue-watcher", "-d", "/edx/etc/xqueue_watcher"]
