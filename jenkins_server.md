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
>http://server-ip:8080
>
first time it will ask for a password that can be found in container logs
```bash
docker ps # get container ip
docker logs <container-ip>
```

create a new user
set url to elastic url for jenkins 

***

### install gitlab plugins in jenkins and amazon ec2 plugin
1.Manage Jenkins
2. plugins
3. available plugins
4. search and mark ***amazon ec2*** , ***gitlab***

***

## connect jenkins controller to gitlab repository server using token

### to to gitlab
1. Repository  
2. settings 
3. access token 
4. add new token
5. pick a name , check write/read repository 
6. create token   

***you will get a token save it***

### go to jenkins
1. settings 
2. Credentials 
3. add Credentials 
4. username with paswword 
5. paste the token , choose a username

***

# IAM policy
1. search IAM 
2. create policy 
3. copy/paste the given json 
4. name it JenkinsEC2AgentPolicy 
5. create policy 
```yml
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
6. search and choose for policy JenkinsEC2AgentPolicy 
7. create new IAM user   

##### after the user is created  
1. press Security credentials 
2. Create access key   

### worker key pair
key need to be ***RSA*** make one 
1. settings 
2. Credentials 
3. add Credentials 
4. SSH username with private key
5. paste the private key you made in aws 
6. choose a username

***

##### back in jenkins make an aws credentials to user 
1. settings 
2. credentials 
3. AWS credentials 
4. put secret and public access key

***
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

***

## define in Jenkins to fetch Jenkinsfile from gitlab repository

### in the job configure scroll down to pipline
1. **Definition** : Pipeline script from SCM
2. **SCM**: GIT
3. **Repository**:  
     **RepositoryURL**: the gitlab repository url using https
     **Credentials**: the one you made before the token



*** 
### Jenkins cloud
1. setting 
2. cloud 
3. new cloud 
4. **name**: worker 
4. ***Amazon EC2 Credentials***: choose the one you made
5. **Region**: your ec2 region
5. ***EC2 Key Pair's Private Key***:the key you made  

***press test connection to check if you are connected successful***


### AMI Template to launch with agent Node
1. ***AMI ID***:your AMI
2. ***instance type***:t3.micro
3. ***security group name***: 
4. ***Remote user***:ubuntu
5. ***AMI Type***: unix
6. ***Labels***:same as jenkins file 
7. ***idle termination***:10
8. press advanced
9. ***number of executors***:1
10. ***subnet ID for VPC***:<your ec2 subnet id>
11. ***Minimum number of instances***:0
12. ***Instance Cap***:1
13. ***Host Key Verification Strategy***: check-new-soft

### AMI how to make 
create a new instance
1. **AMI**:ubuntu 24.04
2. **instance**:t3.micro
3. **keypair**:the RSA key we made for agent
4. **security group**:<your agent security group>
5. launch instance
6. login into the instance
7. in your terminal
```bash
ssh -i "<keypair> ubuntu@<ec2_ip>"
```
8. inside the instance
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y openjdk-21-jre-headless
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
sudo apt install -y python3-pip
sudo pip3 install pylint --break-system-packages
history -c
sudo cloud-init clean
sudo rm -f /etc/ssh/ssh_host_*
```
9. back in **aws** press the image 
10. right click image and template 
11. create image