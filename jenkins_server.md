# creating jenkins server inside a container in ec2 
ami ubuntu 24.04
instance : t3.medium
security group 
ssh my ip
http my gitlab my webapp
storage 50gb
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
  # Init container: prepares truststore with custom CA certificates
  cert-init:
    image: jenkins/jenkins:lts-jdk21
    user: root
    volumes:
      - ./custom-certs:/certs:ro
      - jenkins-cacerts:/cacerts-volume
    command: >
      bash -c '
        cp "$${JAVA_HOME}/lib/security/cacerts" /cacerts-volume/cacerts &&
        for cert in /certs/*.crt /certs/*.pem; do
          [ -f "$$cert" ] || continue;
          alias="custom-$$(basename "$${cert%.*}")";
          "$${JAVA_HOME}/bin/keytool" -importcert -noprompt \
            -keystore /cacerts-volume/cacerts \
            -storepass changeit \
            -alias "$$alias" \
            -file "$$cert" || true;
        done &&
        echo "Custom CA certificates imported successfully"
      '

  # Main Jenkins container
  jenkins:
    image: jenkins/jenkins:lts-jdk21
    depends_on:
      cert-init:
        condition: service_completed_successfully
    restart: on-failure
    ports:
      - "8080:8080"
      - "50000:50000"
    volumes:
      - jenkins_home:/var/jenkins_home
      - jenkins-cacerts:/cacerts:ro
    environment:
      JAVA_OPTS: "-Djavax.net.ssl.trustStore=/cacerts/cacerts -Djavax.net.ssl.trustStorePassword=changeit"

volumes:
  jenkins_home:
  jenkins-cacerts:
```
## Enter jenkins 
>http://server-ip:8080
>
first time it will ask for a password that can be found in container logs
```bash
docker ps # get container ip
docker logs <container-ip>
```

create a new user
set url to elastic url for jenkins 

# in order to give the jenkins the cerfitication
first I need to move the jenkins ec2 key from local to the gitlab , weatherapp ec2 
```bash
scp -i "gitlab.pem/weatherapp.pem" master_jenkins.pem ubuntu@gitlab/weatherapp_server_ip:~
```

insdie each of the instance i need to move my key and crt files 

```bash
sudo scp -i "/path/to/master_jenkins.pem" server.key server.crt ubuntu@jenkins-server-ip:~/custom-certs```
```

## install gitlab plugins in jenkins 

## create a ssh key 
```bash
ssh-keygen -t ed25519 -C "jenkins@yourdomain.com"
```

## inside gitlab do 
> Repository -> settings -> Repository -> Deploy keys -> add new key
paste the value of the key -> add key

```bash
cat ~/.ssh/id_ed25519.pub
```
## inside jenkins do 
> settings -> Credentials -> add Credentials -> copy paste the value of the private key -> add key

```bash
cat ~/.ssh/id_ed25519
```

## then to help first time fingerprint :
>Manage Jenkins -> Security -> Git Host Key Verification Configuration
Set to "Accept first connection"


## to ignore the https self cert
>GIT_SSL_NO_VERIFY=true git push origin main

# Set Up GitLab → Jenkins Webhook
 
## Jenkins
 
1. Start a new job.
2. Under **Build Triggers**, check **"Build when a change is pushed to GitLab"** — this reveals a webhook URL. Save it.
3. Check **Push events**.
4. Click **Advanced → Generate** to create a secret token. Copy it.
## GitLab
 
1. Go to your repository → **Settings → Webhooks → Add new webhook**.
2. **URL**: paste the URL from Jenkins. This tells GitLab where to send the trigger.
3. **Secret Token**: paste the token you generated in Jenkins.
4. Save.
## How the token works
 
The generated token is a shared secret. GitLab sends it in the POST request header, and Jenkins checks it to confirm the webhook actually came from GitLab

### self ssl ceritfication error 

```bash
git config http.sslVerify false
```

## in the job configure scroll down to pipline
1. **Definition** : Pipeline script from SCM
2. **SCM**: GIT
3. **Repository**:  
     **RepositoryURL**: the gitlab repository url using ssh
     **Credentials**: the one you made before with the ssh key


### add amazon ec2 plugin

### in amazon enter access key add a new one also create a new key pair the key must be RSA for the spot instance

### then in jenkins go to settings -> credintals -> AWS credintals -> put secert and public access key


### go to setting cloud -> new cloud -> Amazon EC2 Credentials use the one you made -> EC2 Key Pair's Private Key
