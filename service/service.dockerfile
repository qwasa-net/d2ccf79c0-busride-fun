FROM python:3-slim

WORKDIR /service

COPY requirements.txt /service/requirements.txt

RUN --mount=type=cache,mode=0755,id=pip-cache,target=/var/pip-cache PIP_CACHE_DIR=/var/pip-cache \
    pip install --requirement /service/requirements.txt

COPY ./service /service/service

ENV PYTHONPATH=/service/service
ENV PYTHONUNBUFFERED=1

USER nobody

CMD ["python", "-m", "service"]
