#!/usr/bin/env python3
"""
Script per configurare Amazon ECR per GymApp
Crea il repository ECR e configura le policy necessarie per Beanstalk
"""

import boto3
import json
import logging
from botocore.exceptions import ClientError, NoCredentialsError

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ECRManager:
    def __init__(self, region='us-east-1'):
        """
        Inizializza il manager ECR
        
        Args:
            region (str): Regione AWS dove creare le risorse
        """
        try:
            self.ecr_client = boto3.client('ecr', region_name=region)
            self.iam_client = boto3.client('iam', region_name=region)
            self.region = region
            logger.info(f"Inizializzato ECRManager per regione: {region}")
        except NoCredentialsError:
            logger.error("Credenziali AWS non trovate. Configura AWS CLI o variabili d'ambiente.")
            raise
        except Exception as e:
            logger.error(f"Errore nell'inizializzazione: {str(e)}")
            raise

    def create_ecr_repository(self, repository_name="gymapp-frontend"):
        """
        Crea il repository ECR
        
        Args:
            repository_name (str): Nome del repository ECR
            
        Returns:
            dict: Informazioni del repository creato
        """
        try:
            # Verifica se il repository esiste già
            try:
                response = self.ecr_client.describe_repositories(
                    repositoryNames=[repository_name]
                )
                logger.info(f"Repository {repository_name} esiste già")
                return response['repositories'][0]
            except ClientError as e:
                if e.response['Error']['Code'] == 'RepositoryNotFoundException':
                    logger.info(f"Repository {repository_name} non trovato, creazione in corso...")
                else:
                    raise e

            # Crea il repository
            response = self.ecr_client.create_repository(
                repositoryName=repository_name,
                imageScanningConfiguration={'scanOnPush': True},
                imageTagMutability='MUTABLE',
                encryptionConfiguration={'encryptionType': 'AES256'}
            )
            
            repository_uri = response['repository']['repositoryUri']
            logger.info(f"Repository ECR creato: {repository_uri}")
            
            # Aggiungi tags
            self.ecr_client.tag_resource(
                resourceArn=response['repository']['repositoryArn'],
                tags=[
                    {'Key': 'Name', 'Value': 'GymApp Frontend Repository'},
                    {'Key': 'Environment', 'Value': 'production'},
                    {'Key': 'Project', 'Value': 'GymApp'},
                    {'Key': 'ManagedBy', 'Value': 'Python-Boto3'}
                ]
            )
            
            return response['repository']
            
        except ClientError as e:
            logger.error(f"Errore nella creazione del repository: {e}")
            raise
        except Exception as e:
            logger.error(f"Errore generico: {e}")
            raise

    def set_lifecycle_policy(self, repository_name="gymapp-frontend"):
        """
        Configura la lifecycle policy per il repository
        
        Args:
            repository_name (str): Nome del repository ECR
        """
        try:
            lifecycle_policy = {
                "rules": [
                    {
                        "rulePriority": 1,
                        "description": "Keep last 10 tagged images",
                        "selection": {
                            "tagStatus": "tagged",
                            "tagPrefixList": ["v", "latest"],
                            "countType": "imageCountMoreThan",
                            "countNumber": 10
                        },
                        "action": {
                            "type": "expire"
                        }
                    },
                    {
                        "rulePriority": 2,
                        "description": "Delete untagged images older than 1 day",
                        "selection": {
                            "tagStatus": "untagged",
                            "countType": "sinceImagePushed",
                            "countUnit": "days",
                            "countNumber": 1
                        },
                        "action": {
                            "type": "expire"
                        }
                    }
                ]
            }
            
            self.ecr_client.put_lifecycle_policy(
                repositoryName=repository_name,
                lifecyclePolicyText=json.dumps(lifecycle_policy)
            )
            
            logger.info(f"Lifecycle policy configurata per {repository_name}")
            
        except ClientError as e:
            logger.error(f"Errore nella configurazione lifecycle policy: {e}")
            raise

    def set_repository_policy(self, repository_name="gymapp-frontend"):
        """
        Configura la policy del repository per permettere accesso a Beanstalk
        
        Args:
            repository_name (str): Nome del repository ECR
        """
        try:
            # Policy che permette a Beanstalk di pullare le immagini
            repository_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AllowBeanstalkAccess",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": [
                                "elasticbeanstalk.amazonaws.com",
                                "ec2.amazonaws.com"
                            ]
                        },
                        "Action": [
                            "ecr:GetDownloadUrlForLayer",
                            "ecr:BatchGetImage",
                            "ecr:BatchCheckLayerAvailability"
                        ]
                    },
                    {
                        "Sid": "AllowCrossAccountAccess",
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": f"arn:aws:iam::{boto3.client('sts').get_caller_identity()['Account']}:root"
                        },
                        "Action": [
                            "ecr:GetDownloadUrlForLayer",
                            "ecr:BatchGetImage",
                            "ecr:BatchCheckLayerAvailability",
                            "ecr:PutImage",
                            "ecr:InitiateLayerUpload",
                            "ecr:UploadLayerPart",
                            "ecr:CompleteLayerUpload"
                        ]
                    }
                ]
            }
            
            self.ecr_client.set_repository_policy(
                repositoryName=repository_name,
                policyText=json.dumps(repository_policy)
            )
            
            logger.info(f"Repository policy configurata per {repository_name}")
            
        except ClientError as e:
            logger.error(f"Errore nella configurazione repository policy: {e}")
            raise

    def create_beanstalk_service_role(self):
        """
        Crea il service role per Beanstalk con permessi ECR
        
        Returns:
            str: ARN del ruolo creato
        """
        try:
            role_name = "aws-elasticbeanstalk-ec2-role-ecr"
            
            # Verifica se il ruolo esiste già
            try:
                response = self.iam_client.get_role(RoleName=role_name)
                logger.info(f"Ruolo {role_name} esiste già")
                return response['Role']['Arn']
            except ClientError as e:
                if e.response['Error']['Code'] != 'NoSuchEntity':
                    raise e

            # Trust policy per il ruolo
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "ec2.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
            
            # Crea il ruolo
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="Ruolo per Beanstalk con accesso ECR",
                Tags=[
                    {'Key': 'Name', 'Value': 'Beanstalk ECR Role'},
                    {'Key': 'Project', 'Value': 'GymApp'}
                ]
            )
            
            # Allega le policy necessarie
            policies = [
                "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
                "arn:aws:iam::aws:policy/AWSElasticBeanstalkWebTier",
                "arn:aws:iam::aws:policy/AWSElasticBeanstalkWorkerTier"
            ]
            
            for policy_arn in policies:
                self.iam_client.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy_arn
                )
            
            # Crea l'instance profile
            try:
                self.iam_client.create_instance_profile(InstanceProfileName=role_name)
                self.iam_client.add_role_to_instance_profile(
                    InstanceProfileName=role_name,
                    RoleName=role_name
                )
            except ClientError as e:
                if e.response['Error']['Code'] != 'EntityAlreadyExists':
                    raise e
            
            logger.info(f"Ruolo IAM creato: {response['Role']['Arn']}")
            return response['Role']['Arn']
            
        except ClientError as e:
            logger.error(f"Errore nella creazione del ruolo IAM: {e}")
            raise

    def get_login_command(self, repository_name="gymapp-frontend"):
        """
        Genera il comando per il login Docker a ECR
        
        Args:
            repository_name (str): Nome del repository ECR
            
        Returns:
            dict: Comandi per login e push
        """
        try:
            # Ottieni il token di autorizzazione
            response = self.ecr_client.get_authorization_token()
            token = response['authorizationData'][0]['authorizationToken']
            registry = response['authorizationData'][0]['proxyEndpoint']
            
            # Ottieni l'URI del repository
            repo_response = self.ecr_client.describe_repositories(
                repositoryNames=[repository_name]
            )
            repository_uri = repo_response['repositories'][0]['repositoryUri']
            
            commands = {
                'docker_login': f'aws ecr get-login-password --region {self.region} | docker login --username AWS --password-stdin {registry}',
                'docker_tag': f'docker tag {repository_name}:latest {repository_uri}:latest',
                'docker_push': f'docker push {repository_uri}:latest',
                'repository_uri': repository_uri
            }
            
            return commands
            
        except ClientError as e:
            logger.error(f"Errore nel recupero comandi login: {e}")
            raise

    def setup_complete_ecr(self, repository_name="gymapp-frontend"):
        """
        Configura completamente ECR per l'uso con Beanstalk
        
        Args:
            repository_name (str): Nome del repository ECR
            
        Returns:
            dict: Informazioni complete della configurazione
        """
        try:
            logger.info("=== Inizio configurazione ECR per GymApp ===")
            
            # 1. Crea repository ECR
            repository = self.create_ecr_repository(repository_name)
            
            # 2. Configura lifecycle policy
            self.set_lifecycle_policy(repository_name)
            
            # 3. Configura repository policy
            self.set_repository_policy(repository_name)
            
            # 4. Crea ruolo IAM per Beanstalk
            role_arn = self.create_beanstalk_service_role()
            
            # 5. Genera comandi Docker
            docker_commands = self.get_login_command(repository_name)
            
            result = {
                'repository_name': repository_name,
                'repository_uri': repository['repositoryUri'],
                'repository_arn': repository['repositoryArn'],
                'registry_id': repository['registryId'],
                'iam_role_arn': role_arn,
                'docker_commands': docker_commands
            }
            
            logger.info("=== Configurazione ECR completata ===")
            logger.info(f"Repository URI: {result['repository_uri']}")
            logger.info(f"IAM Role ARN: {result['iam_role_arn']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Errore nella configurazione completa: {e}")
            raise

def main():
    """
    Funzione principale per l'esecuzione dello script
    """
    try:
        # Configura i parametri
        REGION = 'us-east-1'  # Cambia con la tua regione
        REPOSITORY_NAME = 'gymapp-frontend'
        
        # Inizializza il manager ECR
        ecr_manager = ECRManager(region=REGION)
        
        # Configura ECR
        result = ecr_manager.setup_complete_ecr(REPOSITORY_NAME)
        
        # Stampa il riassunto
        print("\n" + "="*60)
        print("CONFIGURAZIONE ECR COMPLETATA")
        print("="*60)
        print(f"Repository Name: {result['repository_name']}")
        print(f"Repository URI: {result['repository_uri']}")
        print(f"Registry ID: {result['registry_id']}")
        print(f"IAM Role ARN: {result['iam_role_arn']}")
        print("\nComandi Docker:")
        print(f"1. Login: {result['docker_commands']['docker_login']}")
        print(f"2. Tag: {result['docker_commands']['docker_tag']}")
        print(f"3. Push: {result['docker_commands']['docker_push']}")
        print("\nPer Beanstalk, usa questo URI:")
        print(f"{result['repository_uri']}:latest")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Errore nell'esecuzione: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())