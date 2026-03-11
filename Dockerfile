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

WORKDIR /edx/app/xqueue_watcher
COPY requirements /edx/app/xqueue_watcher/requirements
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements/production.txt

COPY . /edx/app/xqueue_watcher

USER app

CMD ["python", "-m", "xqueue_watcher", "-d", "/edx/etc/xqueue_watcher"]

FROM base AS edx.org
USER root
RUN pip install --no-cache-dir newrelic
USER app
CMD ["newrelic-admin", "run-program", "python", "-m", "xqueue_watcher", "-d", "/edx/etc/xqueue_watcher"]
