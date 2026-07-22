# creating weather app server inside a container in ec2 
### ami
ubuntu 24.04
***
### instance
t3.micro
***
### security group 
ssh my ip
http my gitlab my webapp
***
### storage 
30gb
***

# connect to my ec2 using ssh 
```bash
chmod 400 ssh_key.pem
ssh -i "ssh_key" ubuntu@<server_ip>
```
***

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker $USER # then log out and back in
```

## clone the repository
```bash
git clone https://github.com/TomerBahar22/Weather_app.git
cd Weather_app
```

***

Create `.env` with your API key. This file is in both `.gitignore` and `.dockerignore` — it never reaches the repo or an image layer:
```bash
touch .env
vim .env
```
```
API_WEATHER=your_api_key
```
## Generate the SSL certificate for weatherforcast.click domain

```bash
sudo certbot certonly --standalone -d weatherforcast.click
```

```bash
docker compose up -d
```

# error 
need to change the git repository remove the build file and change compose from build to 
image: tomerbahar2/weather_app-web:latest