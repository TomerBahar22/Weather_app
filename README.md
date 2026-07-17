# Weather App

This is a Flask-based web application that lets a user look up current weather information for a given location.

**How it works:**
- The user visits the site and requests weather data (e.g., by entering a city/country name).
- The Flask backend (`app.py`) receives the request and calls an external weather API (WeatherAPI) using an API key.
- The API key is read from the environment at runtime (`os.getenv("API_WEATHER")`) — never hardcoded in the source, and never baked into a Docker image.
- The app parses the API's response and renders the result using an HTML template (`templates/home.html`).
- If a request fails or an invalid location is given, a not-found page is shown instead (`templates/not_found.html`).


**Two deployment paths are documented:**
- **[Docker Compose](#docker-deployment)** — one command, runs anywhere. Works locally or on EC2.
- **[Manual EC2 setup](#manual-ec2-deployment)** — the same stack configured by hand with systemd and system-level nginx. Kept as documentation of what Compose automates.

---

# Docker Deployment

## Prerequisites

**Local (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install docker.io docker-compose-plugin -y
sudo usermod -aG docker $USER
```
Log out and back in for the group change to take effect.

**On an EC2 instance (Amazon Linux 2023)** — see [Running on EC2](#running-on-ec2) below.

You'll also need a WeatherAPI key from [weatherapi.com](https://www.weatherapi.com/).

## 1. Clone and configure

```bash
git clone https://github.com/TomerBahar22/Weather_app.git
cd Weather_app
```

Create `.env` with your API key. This file is in both `.gitignore` and `.dockerignore` — it never reaches the repo or an image layer:
```bash
cp .env.example .env
vim .env
```
```
API_WEATHER=your_api_key
```

## 2. Generate the SSL certificate

`ssl/` is gitignored — generate certs locally:
```bash
mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/selfsigned.key \
  -out ssl/selfsigned.crt \
  -subj "/CN=localhost"
```
(On EC2, use `-subj "/CN=<ec2-public-ip>"` instead.)

## 3. Run

**Option A — build from source (default):**
```bash
docker compose up --build
```

**Option B — pull a prebuilt image:**

Build and push once:
```bash
docker push tomerbahar2/weather_app-web
```

Then in `docker-compose.yml`, replace `build: .` with:
```yaml
web:
  image: tomerbahar2/weather_app-web
```
```bash
docker compose up
```

Option A keeps the repo self-contained. Option B skips the build step on the target machine and is the realistic production pattern — CI builds and pushes; servers only pull.

Reachable at `https://localhost:9090` (browser will warn about the self-signed cert — expected).

## Project structure

```
Weather_app/
├── app.py                 # Flask application
├── templates/             # HTML templates
├── requirements.txt
├── Dockerfile             # builds the web (gunicorn) image
├── docker-compose.yml     # orchestrates web + nginx
├── nginx.conf             # main nginx config — rate-limit zones live here
├── myapp.conf             # server block: SSL, proxy, limits
├── .env.example
├── .dockerignore
├── .env                   # gitignored
└── ssl/                   # gitignored
```

## How it's wired

| | |
|---|---|
| `web` container | Gunicorn on `0.0.0.0:8000`, not published to the host |
| `nginx` container | Listens on 443 (SSL), published as host `9090` |
| Traffic flow | `localhost:9090` → nginx:443 → `web:8000` |
| Service discovery | `proxy_pass http://web:8000` — resolved by Docker's embedded DNS |

**Why `0.0.0.0:8000`, not `127.0.0.1:8000`:** in the manual setup, nginx and gunicorn share a machine, so loopback works. In Docker they're separate network namespaces — `127.0.0.1` inside the web container is unreachable from nginx. Gunicorn must bind all interfaces; nginx must target the service name.

**Why `web` uses `expose`, not `ports`:** publishing 8000 to the host would let clients hit gunicorn directly and bypass nginx — skipping SSL and rate limiting entirely. `expose` keeps it reachable only from other containers on the Compose network.

**Why `nginx.conf` is a full copy, not a snippet:** `limit_req_zone` and `limit_conn_zone` must live in the `http {}` block. Since `conf.d/*.conf` files are included *inside* `http {}`, there's no way to add them from `myapp.conf` — the whole file has to be owned and mounted.

## Common tasks

```bash
docker compose up -d --build          # rebuild and run detached
docker compose logs -f web            # follow gunicorn logs
docker compose logs -f nginx          # follow access/error logs
docker compose restart nginx          # reload after editing myapp.conf — bind-mounted, no rebuild needed
docker compose down                   # stop and remove
docker compose exec nginx nginx -T    # print merged nginx config — verifies mounts loaded
docker compose exec nginx curl http://web:8000   # test container-to-container reachability
```

## Troubleshooting

**`SSL routines::wrong version number`** — nginx is serving plain HTTP on the port you hit, meaning your `myapp.conf` didn't load. Check `docker compose logs nginx` for an `[emerg]` line and `docker compose exec nginx nginx -T` to see what config actually merged.

**`Temporary failure in name resolution`** — the container can't resolve external domains. Docker's embedded resolver (`127.0.0.11`) forwards external queries upstream to whatever the host's resolver config says; on Ubuntu with systemd-resolved (or under Docker Desktop's VM), that forwarding target can be unreachable from inside a container namespace. Override it:

```yaml
services:
  web:
    dns:
      - 8.8.8.8
      - 1.1.1.1
```

Or daemon-wide in `/etc/docker/daemon.json`:
```json
{ "dns": ["8.8.8.8", "1.1.1.1"] }
```
then `sudo systemctl restart docker`.

This only affects *external* lookups — service names like `web` are answered by `127.0.0.11` directly and were never affected.

**`port is already allocated`** — something else holds the host port. Find it with `sudo lsof -i :9090`. A leftover host-level nginx from the manual setup is a likely culprit:
```bash
sudo systemctl stop nginx
sudo systemctl disable nginx
```

**Logs filling the disk** — the default `json-file` driver has no size cap. Add rotation in `/etc/docker/daemon.json`:
```json
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
```

## Running on EC2

The Docker setup runs unchanged on EC2 — only the Docker install differs.

**1. Connect** (see [manual section](#1-connect-to-the-ec2-instance) for key permissions and Security Group rules — same requirements: TCP 22 for SSH, TCP 9090 for the app).

**2. Install Docker (Amazon Linux 2023):**
```bash
sudo dnf update -y
sudo dnf install -y docker git
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user
newgrp docker
```

**3. Install the Compose plugin:**
```bash
sudo dnf install -y docker-compose-plugin
```
If that package isn't available on your AMI, install the binary directly:
```bash
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -sL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
```

Verify:
```bash
docker version
docker compose version
```

**4. Deploy** — same as local, with the cert CN set to the instance's public IP:
```bash
git clone https://github.com/TomerBahar22/Weather_app.git
cd Weather_app
cp .env.example .env && vim .env

mkdir -p ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/selfsigned.key \
  -out ssl/selfsigned.crt \
  -subj "/CN=<ec2-public-ip>"

docker compose up -d --build
```

Reachable at `https://<ec2-public-ip>:9090`.

**Notes:**
- **Don't install nginx or python on the host** — both run in containers. A host-level nginx will fight for port 9090.
- **The Security Group is unchanged** from the manual setup — Docker's port publishing inserts iptables DNAT rules on the instance, but AWS's Security Group is still the outer gate.
- **`newgrp docker`** applies the group change in the current shell; without it you'd need to log out and back in before running docker without `sudo`.

---

# Manual EC2 Deployment

> Kept as reference. Same architecture as the Docker setup, configured by hand — useful for understanding what Compose automates.

## 1. Connect to the EC2 instance

Restrict the downloaded key pair's permissions (required — SSH refuses to use a key file that's readable by others):
```bash
chmod 400 your-key.pem
```

SSH into the instance using the key pair (username depends on the AMI: `ubuntu` for Ubuntu AMIs, `ec2-user` for Amazon Linux):
```bash
ssh -i your-key.pem ec2-user@<ec2-public-ip>
```

the EC2 **Security Group** must allow inbound traffic on:
- TCP 22 (SSH) — source: your IP
- TCP 9090 (HTTPS/app) — source: your IP, or `0.0.0.0/0` for public access

---

## 2. Install dependencies

Update package lists and install nginx, Python venv tools, pip, and git:
```bash
sudo yum update
sudo yum install nginx python3-venv python3-pip git -y
```

Clone the app repo and move into it:
```bash
git clone https://github.com/TomerBahar22/Weather_app.git
cd Weather_app
```

Create and activate a virtual environment, then install dependencies. (`gunicorn` should be listed in `requirements.txt` — don't also install it via the system package manager, since that creates a separate system-wide copy outside the venv.)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create the `.env` file with your WeatherAPI key
```bash
vim .env
```
```
API_WEATHER=your_api_key
```

Export it into the environment before running gunicorn (or set it in the systemd unit — see step 8):
```bash
export $(cat .env | xargs)
```

---

## 3. SSL certificate

Generate a self-signed SSL certificate
```bash
sudo mkdir -p /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/selfsigned.key \
  -out /etc/nginx/ssl/selfsigned.crt \
  -subj "/CN=<ec2-public-ip>"
```

---

## 4. Nginx site config

Create the config file:
```bash
sudo vim /etc/nginx/conf.d/myapp.conf
```

Paste this inside it:
```nginx
server {
    listen 9090 ssl;
    server_name <ec2-public-ip>;

    ssl_certificate /etc/nginx/ssl/selfsigned.crt;
    ssl_certificate_key /etc/nginx/ssl/selfsigned.key;

    location / {
        limit_req zone=req_limit;
        limit_conn conn_limit 5;

        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 5. Rate limiting zones

Define the rate-limit/connection-limit zones — must live in the `http {}` block of the main config, not the site config:
```bash
sudo vim /etc/nginx/nginx.conf
```

Add inside `http {}`:
```nginx
limit_req_zone $binary_remote_addr zone=req_limit:10m rate=1r/s;
limit_conn_zone $binary_remote_addr zone=conn_limit:10m;
```

---

## 6. Apply the Nginx config

Test the config for syntax errors before applying:
```bash
sudo nginx -t
```

Restart nginx to apply the new config:
```bash
sudo systemctl restart nginx
```

---

## 7. Run the app

Run Gunicorn, binding it to localhost:8000 (nginx proxies to this):
```bash
gunicorn --bind 127.0.0.1:8000 app:app
```

For persistence beyond this SSH session, run Gunicorn as a **systemd service** instead (see below) so it survives logout/reboot.

---

## 8. (Optional) systemd service for Gunicorn

```bash
sudo vim /etc/systemd/system/myapp.service
```
```ini
[Unit]
Description=Gunicorn instance for Weather App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/Weather_app
EnvironmentFile=/home/ubuntu/Weather_app/.env
ExecStart=/home/ubuntu/Weather_app/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now myapp
```
