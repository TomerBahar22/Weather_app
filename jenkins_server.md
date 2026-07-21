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

first time it will ask for a password that can be found in container logs
```bash
docker ps # get container ip
docker logs <container-ip>
```

create a new user
set url to elastic url for jenkins 
