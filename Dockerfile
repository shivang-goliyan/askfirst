# The app runs on CPU. The baked curve is the headline and needs no GPU, so this image
# stays small and the page is up whether or not a droplet is alive.
#
# Set ASKFIRST_VLLM_URL at run time and the live endpoints start scoring against the open
# model instead of the baseline. Nothing else changes; the response says which one answered.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    PORT=7860

WORKDIR /app

RUN pip install --no-cache-dir \
      "fastapi==0.115.6" \
      "uvicorn==0.34.0" \
      "pyyaml==6.0.2" \
      "numpy==2.3.5" \
      "openai==1.59.6"

COPY LICENSE pyproject.toml ./
COPY src ./src
COPY ui ./ui

RUN useradd -m -u 1000 app && chown -R app:app /app
USER app

EXPOSE 7860

# Two workers, because an assessment is CPU-bound numpy under the GIL and one process serialises
# them: 24 simultaneous requests took 11 seconds on one worker. Two processes hold ~136 MB of the
# 400 MB cap, which leaves room on a box that is running other people's things.
CMD ["sh", "-c", "uvicorn askfirst.api:app --host 0.0.0.0 --port ${PORT} --workers 2"]
