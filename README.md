# Infrastructure Setup — Jenkins Server & Weather App Server

---

# Part 1: Jenkins server inside a container in EC2

### ami
ubuntu 24.04
### instance
t3.medium
### security group
ssh my ip
http my gitlab my webapp
### storage
50gb

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
sudo usermod -aG docker $USER
```

# inside the ec2 make a docker compose
```bash
touch docker-compose.yml
vim docker-compose.yml
```

***

### the docker compose file

```yml
services:
  jenkins:
    image: jenkins/jenkins:lts-jdk21
    container_name: jenkins
    restart: on-failure
    ports:
      - "8080:8080"
      - "50000:50000"
    volumes:
      - jenkins_home:/var/jenkins_home

volumes:
  jenkins_home:
```

## Enter jenkins
> http://server-ip:8080

first time it will ask for a password that can be found in container logs
```bash
docker ps            # get the container name
docker logs jenkins  # the initial admin password appears in the log
```

create a new user
set url to elastic url for jenkins

***

### install gitlab plugin and amazon ec2 plugin in jenkins
1. Manage Jenkins
2. Plugins
3. Available plugins
4. search and mark ***amazon ec2***, ***gitlab***

***

## connect jenkins controller to gitlab repository server using token

### go to gitlab
1. Repository
2. Settings
3. Access tokens
4. Add new token
5. pick a name, check read/write repository
6. create token

***you will get a token — save it***

### go to jenkins
1. Settings
2. Credentials
3. Add Credentials
4. Username with password
5. paste the token as the password, choose a username

***

# IAM policy
1. search IAM
2. create policy
3. copy/paste the given json
4. name it JenkinsEC2AgentPolicy
5. create policy
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Stmt1312295543082",
            "Action": [
                "ec2:DescribeSpotInstanceRequests",
                "ec2:CancelSpotInstanceRequests",
                "ec2:GetConsoleOutput",
                "ec2:RequestSpotInstances",
                "ec2:RunInstances",
                "ec2:StartInstances",
                "ec2:StopInstances",
                "ec2:TerminateInstances",
                "ec2:CreateTags",
                "ec2:DeleteTags",
                "ec2:DescribeInstances",
                "ec2:DescribeKeyPairs",
                "ec2:DescribeRegions",
                "ec2:DescribeImages",
                "ec2:DescribeAvailabilityZones",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeSubnets",
                "iam:ListInstanceProfilesForRole",
                "ec2:GetPasswordData"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ]
}
```

***

# IAM user
1. search IAM
2. IAM users
3. create user
4. choose name
5. attach policy directly
6. search and choose the policy JenkinsEC2AgentPolicy
7. create new IAM user

##### after the user is created
1. press Security credentials
2. Create access key

### worker key pair
key needs to be ***RSA*** — make one
1. Settings
2. Credentials
3. Add Credentials
4. SSH Username with private key
5. paste the private key you made in aws
6. choose a username

***

##### back in jenkins make an aws credential for the IAM user
1. Settings
2. Credentials
3. AWS Credentials
4. put the access key and secret key

***

# Set Up GitLab → Jenkins Webhook

## Jenkins

1. Start a new job.
2. Under **Build Triggers**, check **"Build when a change is pushed to GitLab"** — this reveals a webhook URL. Save it.
3. Check **Push events**.
4. Click **Advanced → Generate** to create a secret token. Copy it.

> **Gotcha — 403 on webhook test:** if GitLab's webhook test returns 403 with `X-Required-Permission: hudson.model.Hudson.Read`, go to **Manage Jenkins → System → GitLab section** and check **"Enable authentication for '/project' end-point"**.

## GitLab

1. Go to your repository → **Settings → Webhooks → Add new webhook**.
2. **URL**: paste the URL from Jenkins. Use the Jenkins **private IP** — both servers are in the same VPC, so the traffic should stay internal.
3. **Secret Token**: paste the token you generated in Jenkins.
4. Save.

## How the token works

The generated token is a shared secret. GitLab sends it in the POST request header, and Jenkins checks it to confirm the webhook actually came from GitLab.

***

## define in Jenkins to fetch Jenkinsfile from gitlab repository

### in the job configure scroll down to pipeline
1. **Definition**: Pipeline script from SCM
2. **SCM**: Git
3. **Repository**:
   - **Repository URL**: the gitlab repository url
   - **Credentials**: the token credential you made before

> **Gotcha — public vs private IP:** when Jenkins and GitLab are in the same VPC, use **private IPs** between them. Traffic to a public IP leaves through the Internet Gateway and comes back as external — so security group rules that reference another security group (or the VPC CIDR) won't match it.

***

### Jenkins cloud
1. Settings
2. Clouds
3. New cloud
4. **name**: worker
5. ***Amazon EC2 Credentials***: choose the one you made
6. **Region**: your ec2 region
7. ***EC2 Key Pair's Private Key***: the RSA key you made

***press test connection to check if you are connected successfully***

### AMI Template to launch with agent Node
1. ***AMI ID***: your AMI
2. ***Instance type***: t3.micro
3. ***Security group name***: your agent security group
4. ***Remote user***: ubuntu
5. ***AMI Type***: unix
6. ***Labels***: same as in the Jenkinsfile (`worker`)
7. ***Idle termination time***: 10
8. press advanced
9. ***Number of executors***: 1
10. ***Subnet ID for VPC***: <your ec2 subnet id>
11. ***Minimum number of instances***: 0
12. ***Instance Cap***: 1
13. ***Host Key Verification Strategy***: check-new-soft

### AMI how to make
create a new instance
1. **AMI**: ubuntu 24.04
2. **instance**: t3.micro
3. **keypair**: the RSA key we made for the agent
4. **security group**: <your agent security group>
5. launch instance
6. login into the instance
```bash
ssh -i "<keypair>" ubuntu@<ec2_ip>
```
7. inside the instance
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y openjdk-21-jre-headless
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
sudo apt install -y python3-pip
sudo pip3 install pylint --break-under-system-packages
history -c
sudo cloud-init clean
sudo rm -f /etc/ssh/ssh_host_*
```

> **Why `sudo pip3` for pylint:** installing with sudo puts pylint in `/usr/local/bin`, which is on the PATH for Jenkins' non-interactive shell. A `--user` install goes to `~/.local/bin` and the agent gets `pylint: not found`.

8. back in **aws** press the instance
9. Actions → Image and templates
10. create image

> **Important:** create the AMI immediately after the last commands — **don't reboot first**. Rebooting runs cloud-init's "first boot" on this instance, baking regenerated host keys into the image.

***

## SSH key credential for deploying to the weather app server
1. Jenkins Settings
2. Credentials
3. New
4. **SSH Username with private key**
5. **Private key**: the weather-forecast app server's private key
```bash
cat "weather-forecast.pem"
```

---

# Part 2: Weather app server inside a container in EC2

### ami
ubuntu 24.04
### instance
t3.micro
### security group
ssh my ip
http/https open (80 + 443 — certbot needs 80, the site serves on 443)
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
sudo apt install -y docker.io docker-compose-v2 certbot
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

## Generate the SSL certificate for the weather-forecast.click domain

```bash
sudo certbot certonly --standalone -d weather-forecast.click
```

> **Gotcha — certbot 403 on a fresh GoDaddy domain:** GoDaddy may auto-attach a Website Builder page or a Forwarding rule to a new domain. Delete the extra `@` A record and any Forwarding rule, then verify `dig weather-forecast.click +short` returns **only** your EC2 IP before retrying certbot.

## Run

```bash
docker compose up -d
```

> The compose file pulls the CI-built image (`image: tomerbahar2/weather_app-web:latest`) instead of building from source — CI builds and pushes, the server only pulls.