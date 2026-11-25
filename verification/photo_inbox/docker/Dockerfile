# The private photo inbox (#626) as one image: Python, the inbox's packages, Tesseract with the
# collection's languages (#658) and the repository code the inbox imports. Build from the
# repository root:
#
#     docker build -f verification/photo_inbox/docker/Dockerfile -t snoredex-inbox .
#
# The catalogue and the photo archive are not baked in: compose.yaml mounts their checkouts and its
# sync service keeps them current. A code or dependency change needs a rebuild.
FROM python:3.12-slim-bookworm

# Tesseract and its language data for the collection's languages; git for the sync service and, with
# ssh, for the intake run's push to the photo archive (#659)
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git openssh-client tesseract-ocr \
      tesseract-ocr-eng tesseract-ocr-jpn tesseract-ocr-deu tesseract-ocr-chi-sim tesseract-ocr-chi-tra \
      tesseract-ocr-kor tesseract-ocr-fra tesseract-ocr-ita tesseract-ocr-spa tesseract-ocr-por \
      tesseract-ocr-ind tesseract-ocr-tha tesseract-ocr-rus tesseract-ocr-pol tesseract-ocr-nld \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY verification/photo_inbox/requirements.txt verification/photo_inbox/requirements.txt
RUN pip install --no-cache-dir -r verification/photo_inbox/requirements.txt

# only what the inbox runs or imports: its own folder, the repository scripts and the verification
# modules it uses for covers and card faces (Dockerfile.dockerignore keeps out data, images, evidence)
COPY scripts scripts
COPY verification verification

# a fixed, unprivileged user; PUID and PGID match the owner of the mounted folders on the host
ARG PUID=1000
ARG PGID=1000
RUN groupadd --gid "${PGID}" inbox && useradd --uid "${PUID}" --gid inbox --no-create-home inbox \
 && mkdir -p /data /checkouts && chown inbox:inbox /data /checkouts \
 && git config --system --add safe.directory '*'
USER inbox

# the commit and time this image was built from, shown in the inbox's version line (#666);
# docker/update.sh passes both, and without them the line says "unbekannt"
ARG GIT_COMMIT=
ARG BUILT_AT=
ENV PYTHONUNBUFFERED=1 PORT=8765 INBOX_COMMIT=${GIT_COMMIT} INBOX_BUILT_AT=${BUILT_AT}
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/', timeout=4)"

ENTRYPOINT ["sh", "verification/photo_inbox/docker/entrypoint.sh"]
