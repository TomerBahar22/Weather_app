Weather App — Description

This is a Flask-based web application that lets a user look up current 
weather information for a given location.

How it works:
- The user visits the site and requests weather data (e.g., by entering 
  a city name).
- The Flask backend (app.py) receives the request and calls an external 
  weather API (WeatherAPI) using an API key.
- The API key is stored securely in a .env file and loaded at runtime 
  via python-dotenv, rather than being hardcoded in the source code.
- The app parses the API's response and renders the result using an 
  HTML template (templates/home.html).
- If a request fails or an invalid location is given, a not-found page 
  is shown instead (templates/not_found.html).

Deployment:
- In production, the app is served by Gunicorn (a WSGI server running 
  multiple worker processes) instead of Flask's built-in development 
  server.
- Nginx sits in front of Gunicorn as a reverse proxy, handling HTTPS 
  (via a self-signed SSL certificate), and enforcing rate limiting 
  (1 request/sec per client IP) and connection limiting (max 5 
  concurrent connections per client IP).
- The full stack (Nginx + Gunicorn + Flask) has been tested locally 
  and deployed to an Ubuntu Server virtual machine running under KVM, 
  simulating a real production environment.



# Update package lists and install nginx, Python venv tools, pip, and git
sudo apt update
sudo apt install nginx python3-venv python3-pip git -y

# Clone the app repo and move into it
git clone https://github.com/TomerBahar22/Weather_app.git
cd Weather_app

# Create and activate a virtual environment, then install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create the .env file with your WeatherAPI key (never commit this file)
vim .env
# API_WEATHER=your_api_key

# Generate a self-signed SSL certificate (no public domain, so Let's Encrypt isn't usable)
sudo mkdir -p /etc/nginx/ssl
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/selfsigned.key \
  -out /etc/nginx/ssl/selfsigned.crt \
  -subj "/CN=localhost"

# Create the nginx site config for the app
sudo vim /etc/nginx/sites-available/myapp

# --- paste inside the file ---
server {
    listen 9090 ssl;                # HTTPS on port 9090
    server_name localhost;

    ssl_certificate /etc/nginx/ssl/selfsigned.crt;
    ssl_certificate_key /etc/nginx/ssl/selfsigned.key;

    location / {
        limit_req zone=req_limit;       # 1 request/sec per client IP (zone defined in nginx.conf)
        limit_conn conn_limit 5;        # max 5 concurrent connections per client IP

        proxy_pass http://127.0.0.1:8000;   # forward to Gunicorn
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
# --- end of file contents ---

# Enable the site by symlinking it into sites-enabled, remove the default site
sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Define the rate-limit/connection-limit zones — must live in the http {} block of the main config
sudo vim /etc/nginx/nginx.conf
# inside http {}, add:
#   limit_req_zone $binary_remote_addr zone=req_limit:10m rate=1r/s;
#   limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

# Test the config for syntax errors before applying
sudo nginx -t

# Restart nginx to apply the new config
sudo systemctl restart nginx

# Open the firewall for port 9090
sudo ufw allow 9090/tcp

# Run Gunicorn, binding it to localhost:8000 (nginx proxies to this)
gunicorn --bind 127.0.0.1:8000 app:app