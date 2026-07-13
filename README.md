# Weather App 

This is a Flask-based web application that lets a user look up current weather information for a given location.

**How it works:**
- The user visits the site and requests weather data (e.g., by entering a city/country name).
- The Flask backend (`app.py`) receives the request and calls an external weather API (WeatherAPI) using an API key.
- The API key is stored securely in a `.env` file and loaded at runtime via `python-dotenv`, rather than being hardcoded in the source code.
- The app parses the API's response and renders the result using an HTML template (`templates/home.html`).
- If a request fails or an invalid location is given, a not-found page is shown instead (`templates/not_found.html`).

**Deployment:**
- In production, the app is served by Gunicorn (a WSGI server running multiple worker processes) instead of Flask's built-in development server.
- Nginx sits in front of Gunicorn as a reverse proxy, handling HTTPS (via a self-signed SSL certificate), and enforcing rate limiting (1 request/sec per client IP) and connection limiting (max 5 concurrent connections per client IP).
- Deployed to an AWS EC2 instance (Ubuntu), reachable over SSH via a key pair, with inbound access controlled at two layers: the EC2 Security Group (AWS-level firewall) and Nginx itself.

---

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

Create and activate a virtual environment, then install dependencies. (`gunicorn` should be listed in `requirements.txt` — don't also install it via `apt`, since that creates a separate system-wide copy outside the venv.)
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
ExecStart=/home/ubuntu/Weather_app/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now myapp
```