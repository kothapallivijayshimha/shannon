FROM python:3.12-slim AS tools

# ── Stage 1: install Go (for subfinder, httpx, naabu, amass etc.) ──
RUN apt-get update && apt-get install -y --no-install-recommends \
    golang-go \
    && rm -rf /var/lib/apt/lists/*

ENV GOPATH=/go PATH=/go/bin:$PATH

RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest && \
    go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest && \
    go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest && \
    go install -v github.com/owasp-amass/amass/v4/...@master && \
    go install -v github.com/OJ/gobuster/v3@latest && \
    go install -v github.com/projectdiscovery/katana/cmd/katana@latest


# ── Stage 2: runtime image ──────────────────────────────────────
FROM python:3.12-slim

# Install system-level security tools via apt
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Recon
    nmap \
    dnsrecon \
    whois \
    # Web
    nikto \
    dirb \
    sqlmap \
    wpscan \
    # Password
    john \
    hydra \
    medusa \
    hashcat \
    # Post-exploit
    responder \
    # Wireless
    aircrack-ng \
    kismet \
    bettercap \
    # Forensics
    volatility3 \
    # Utility
    curl \
    wget \
    git \
    netcat-openbsd \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Install Python-based tools via pip
RUN pip install --no-cache-dir \
    shodan==1.31.1 \
    dpath==2.2.0 \
    && rm -rf /root/.cache/pip

# Copy Go binaries from stage 1
COPY --from=tools /go/bin/subfinder /go/bin/httpx /go/bin/naabu /go/bin/amass /go/bin/gobuster /usr/local/bin/

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir . && rm -rf /root/.cache/pip

COPY . .

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -sf http://localhost:8000/ || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
