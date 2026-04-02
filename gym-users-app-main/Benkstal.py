#!/usr/bin/env python3
"""
Script per deployare un'applicazione Docker da ECR ad AWS Elastic Beanstalk
"""

import boto3
import json
import time
from datetime import datetime
from botocore.exceptions import ClientError

# ==============================================================================
# CONFIGURAZIONE - Modifica questi parametri
# ==============================================================================

# Informazioni AWS
AWS_REGION = "us-east-1"  # Cambia con la tua region
AWS_ACCOUNT_ID = "724201375649"  # Il tuo Account ID

# Informazioni ECR
ECR_REPOSITORY_NAME = "gymapp-frontend"  # Nome del repository ECR
IMAGE_TAG = "latest"  # Tag dell'immagine (puoi usare anche lo sha256 specifico)

# Informazioni Elastic Beanstalk
EB_APPLICATION_NAME = "gymapp-frontend"  # Nome dell'applicazione Beanstalk (NON il nome dell'environment!)
EB_ENVIRONMENT_NAME = None  # Lascia None per scegliere interattivamente, oppure specifica: "gymapp-frontend-env"
SOLUTION_STACK = "64bit Amazon Linux 2023 v4.3.5 running Docker"  # Stack per Docker
S3_BUCKET = "elasticbeanstalk-{}-{}".format(AWS_REGION, AWS_ACCOUNT_ID)  # Bucket S3 per Beanstalk

# Impostazioni opzionali
AUTO_SELECT_HEALTHY_ENV = True  # Se True, seleziona automaticamente il primo environment "Green"

# ==============================================================================
# INIZIALIZZAZIONE CLIENT BOTO3
# ==============================================================================

ecr_client = boto3.client('ecr', region_name=AWS_REGION)
eb_client = boto3.client('elasticbeanstalk', region_name=AWS_REGION)
s3_client = boto3.client('s3', region_name=AWS_REGION)


def get_ecr_image_uri():
    """
    Recupera l'URI completo dell'immagine Docker da ECR
    """
    try:
        # Verifica che l'immagine esista
        response = ecr_client.describe_images(
            repositoryName=ECR_REPOSITORY_NAME,
            imageIds=[{'imageTag': IMAGE_TAG}]
        )
        
        if not response['imageDetails']:
            raise Exception(f"Immagine con tag '{IMAGE_TAG}' non trovata nel repository '{ECR_REPOSITORY_NAME}'")
        
        # Costruisci l'URI completo dell'immagine
        image_uri = f"{AWS_ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/{ECR_REPOSITORY_NAME}:{IMAGE_TAG}"
        
        image_digest = response['imageDetails'][0].get('imageDigest', 'N/A')
        image_size = response['imageDetails'][0].get('imageSizeInBytes', 0) / (1024*1024)  # Convert to MB
        pushed_at = response['imageDetails'][0].get('imagePushedAt', 'N/A')
        
        print(f"✓ Immagine trovata su ECR:")
        print(f"  URI: {image_uri}")
        print(f"  Digest: {image_digest}")
        print(f"  Dimensione: {image_size:.2f} MB")
        print(f"  Push date: {pushed_at}")
        
        return image_uri
        
    except ClientError as e:
        print(f"✗ Errore nel recupero dell'immagine da ECR: {e}")
        raise


def create_dockerrun_json(image_uri):
    """
    Crea il file Dockerrun.aws.json per Elastic Beanstalk
    """
    dockerrun_content = {
        "AWSEBDockerrunVersion": "1",
        "Image": {
            "Name": image_uri,
            "Update": "true"
        },
        "Ports": [
            {
                "ContainerPort": 3000,
                "HostPort": 3000
            }
        ],
        "Logging": "/var/log/nginx"
    }
    
    return json.dumps(dockerrun_content, indent=2)


def create_application():
    """
    Crea l'applicazione Elastic Beanstalk se non esiste
    """
    try:
        response = eb_client.create_application(
            ApplicationName=EB_APPLICATION_NAME,
            Description=f"Applicazione {EB_APPLICATION_NAME} - Creata automaticamente"
        )
        print(f"✓ Applicazione '{EB_APPLICATION_NAME}' creata con successo")
        return response
    except ClientError as e:
        if e.response['Error']['Code'] == 'TooManyApplicationsException':
            print(f"✗ Limite di applicazioni raggiunto. Elimina alcune applicazioni non utilizzate.")
        print(f"✗ Errore nella creazione dell'applicazione: {e}")
        raise


def list_environments():
    """
    Lista tutti gli environment disponibili per l'applicazione
    """
    try:
        response = eb_client.describe_environments(
            ApplicationName=EB_APPLICATION_NAME,
            IncludeDeleted=False
        )
        
        environments = response.get('Environments', [])
        
        if not environments:
            print(f"⚠ Nessun environment trovato per l'applicazione '{EB_APPLICATION_NAME}'")
            return []
        
        print(f"\n📋 Environment disponibili per '{EB_APPLICATION_NAME}':")
        print("-" * 80)
        
        for idx, env in enumerate(environments, 1):
            status = env.get('Status', 'Unknown')
            health = env.get('Health', 'Unknown')
            env_name = env.get('EnvironmentName', 'N/A')
            url = env.get('CNAME', 'N/A')
            
            # Emoji per lo stato
            health_emoji = {
                'Green': '✅',
                'Yellow': '⚠️',
                'Red': '❌',
                'Grey': '⚫'
            }.get(health, '❓')
            
            print(f"{idx}. {env_name}")
            print(f"   Status: {status} | Health: {health_emoji} {health}")
            print(f"   URL: {url}")
            print(f"   Version: {env.get('VersionLabel', 'N/A')}")
            print()
        
        return environments
        
    except ClientError as e:
        print(f"✗ Errore nel recupero degli environment: {e}")
        return []


def select_environment():
    """
    Permette all'utente di selezionare un environment
    """
    environments = list_environments()
    
    if not environments:
        print("\n⚠ Nessun environment disponibile. Vuoi crearne uno nuovo? (s/n): ", end='')
        choice = input().strip().lower()
        if choice == 's':
            env_name = input("Inserisci il nome del nuovo environment: ").strip()
            return env_name
        return None
    
    # Se AUTO_SELECT_HEALTHY_ENV è True, seleziona automaticamente il primo Green
    if AUTO_SELECT_HEALTHY_ENV:
        for env in environments:
            if env.get('Health') == 'Green' and env.get('Status') == 'Ready':
                selected_name = env.get('EnvironmentName')
                print(f"🎯 Auto-selezionato environment: {selected_name} (Green)")
                return selected_name
    
    # Altrimenti chiedi all'utente
    print("\n🎯 Seleziona un environment (1-{}), oppure 'n' per crearne uno nuovo: ".format(len(environments)), end='')
    choice = input().strip()
    
    if choice.lower() == 'n':
        env_name = input("Inserisci il nome del nuovo environment: ").strip()
        return env_name
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(environments):
            selected_env = environments[idx]['EnvironmentName']
            print(f"✓ Selezionato: {selected_env}")
            return selected_env
        else:
            print("⚠ Selezione non valida. Uso il primo environment disponibile.")
            return environments[0]['EnvironmentName']
    except ValueError:
        print("⚠ Input non valido. Uso il primo environment disponibile.")
        return environments[0]['EnvironmentName']


def create_environment(version_label):
    """
    Crea l'environment Elastic Beanstalk se non esiste
    """
    try:
        response = eb_client.create_environment(
            ApplicationName=EB_APPLICATION_NAME,
            EnvironmentName=EB_ENVIRONMENT_NAME,
            VersionLabel=version_label,
            SolutionStackName=SOLUTION_STACK,
            Tier={
                'Name': 'WebServer',
                'Type': 'Standard'
            },
            OptionSettings=[
                {
                    'Namespace': 'aws:autoscaling:launchconfiguration',
                    'OptionName': 'IamInstanceProfile',
                    'Value': 'aws-elasticbeanstalk-ec2-role'
                },
                {
                    'Namespace': 'aws:elasticbeanstalk:environment',
                    'OptionName': 'EnvironmentType',
                    'Value': 'SingleInstance'
                },
                {
                    'Namespace': 'aws:ec2:instances',
                    'OptionName': 'InstanceTypes',
                    'Value': 't3.micro'
                }
            ]
        )
        print(f"✓ Environment '{EB_ENVIRONMENT_NAME}' creato con successo")
        print(f"  Status: {response['Status']}")
        return response
    except ClientError as e:
        print(f"✗ Errore nella creazione dell'environment: {e}")
        raise


def upload_to_s3(content, key):
    """
    Carica il file Dockerrun.aws.json su S3
    """
    try:
        # Verifica se il bucket esiste, altrimenti crealo
        try:
            s3_client.head_bucket(Bucket=S3_BUCKET)
        except ClientError:
            print(f"Creazione bucket S3: {S3_BUCKET}")
            if AWS_REGION == 'us-east-1':
                s3_client.create_bucket(Bucket=S3_BUCKET)
            else:
                s3_client.create_bucket(
                    Bucket=S3_BUCKET,
                    CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
                )
        
        # Upload del file
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=content.encode('utf-8')
        )
        
        print(f"✓ File caricato su S3: s3://{S3_BUCKET}/{key}")
        return True
        
    except ClientError as e:
        print(f"✗ Errore nel caricamento su S3: {e}")
        raise


def create_application_version(version_label, s3_key):
    """
    Crea una nuova versione dell'applicazione Beanstalk
    """
    try:
        # Prima verifica se l'applicazione esiste
        try:
            eb_client.describe_applications(ApplicationNames=[EB_APPLICATION_NAME])
            print(f"✓ Applicazione '{EB_APPLICATION_NAME}' trovata")
        except ClientError:
            print(f"⚠ Applicazione '{EB_APPLICATION_NAME}' non trovata. Creazione in corso...")
            create_application()
        
        response = eb_client.create_application_version(
            ApplicationName=EB_APPLICATION_NAME,
            VersionLabel=version_label,
            Description=f"Deploy da ECR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            SourceBundle={
                'S3Bucket': S3_BUCKET,
                'S3Key': s3_key
            },
            AutoCreateApplication=False,
            Process=True
        )
        
        print(f"✓ Application version creata: {version_label}")
        return response
        
    except ClientError as e:
        print(f"✗ Errore nella creazione della versione: {e}")
        raise


def deploy_to_environment(version_label):
    """
    Deploy della nuova versione nell'environment Beanstalk
    """
    try:
        # Verifica se l'environment esiste
        try:
            response = eb_client.describe_environments(
                ApplicationName=EB_APPLICATION_NAME,
                EnvironmentNames=[EB_ENVIRONMENT_NAME]
            )
            
            if not response['Environments']:
                print(f"⚠ Environment '{EB_ENVIRONMENT_NAME}' non trovato. Creazione in corso...")
                return create_environment(version_label)
            
            print(f"✓ Environment '{EB_ENVIRONMENT_NAME}' trovato")
            
        except ClientError:
            print(f"⚠ Environment '{EB_ENVIRONMENT_NAME}' non trovato. Creazione in corso...")
            return create_environment(version_label)
        
        print(f"⏳ Avvio deploy su environment: {EB_ENVIRONMENT_NAME}")
        
        response = eb_client.update_environment(
            ApplicationName=EB_APPLICATION_NAME,
            EnvironmentName=EB_ENVIRONMENT_NAME,
            VersionLabel=version_label
        )
        
        print(f"✓ Deploy avviato!")
        print(f"  Environment ID: {response['EnvironmentId']}")
        print(f"  Status: {response['Status']}")
        
        return response
        
    except ClientError as e:
        print(f"✗ Errore nel deploy: {e}")
        raise


def wait_for_environment_ready(timeout_minutes=10):
    """
    Attende che l'environment sia pronto dopo il deploy
    """
    print(f"\n⏳ Attesa completamento deploy (timeout: {timeout_minutes} minuti)...")
    
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    
    while True:
        try:
            response = eb_client.describe_environments(
                ApplicationName=EB_APPLICATION_NAME,
                EnvironmentNames=[EB_ENVIRONMENT_NAME]
            )
            
            if not response['Environments']:
                print(f"✗ Environment '{EB_ENVIRONMENT_NAME}' non trovato")
                return False
            
            env = response['Environments'][0]
            status = env['Status']
            health = env.get('Health', 'Unknown')
            
            print(f"  Status: {status} | Health: {health}", end='\r')
            
            if status == 'Ready':
                print(f"\n✓ Deploy completato con successo!")
                print(f"  URL: {env.get('CNAME', 'N/A')}")
                print(f"  Health: {health}")
                return True
            
            if status in ['Terminated', 'Terminating']:
                print(f"\n✗ Environment in stato: {status}")
                return False
            
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                print(f"\n⚠ Timeout raggiunto. Status attuale: {status}")
                return False
            
            time.sleep(10)
            
        except ClientError as e:
            print(f"\n✗ Errore durante il controllo dello stato: {e}")
            return False


def main():
    """
    Funzione principale
    """
    print("="*70)
    print("AWS Elastic Beanstalk - Deploy da ECR")
    print("="*70)
    print()
    
    # Variabile globale per l'environment name
    global EB_ENVIRONMENT_NAME
    
    try:
        # 0. Seleziona l'environment se non specificato
        if EB_ENVIRONMENT_NAME is None:
            print("🔍 Step 0: Selezione environment")
            EB_ENVIRONMENT_NAME = select_environment()
            if not EB_ENVIRONMENT_NAME:
                print("✗ Nessun environment selezionato. Uscita.")
                return 1
            print()
        
        # 1. Recupera l'URI dell'immagine da ECR
        print("📦 Step 1: Recupero immagine da ECR")
        image_uri = get_ecr_image_uri()
        print()
        
        # 2. Crea il file Dockerrun.aws.json
        print("📝 Step 2: Creazione Dockerrun.aws.json")
        dockerrun_json = create_dockerrun_json(image_uri)
        print("✓ Dockerrun.aws.json creato")
        print()
        
        # 3. Carica su S3
        print("☁️  Step 3: Upload su S3")
        version_label = f"v{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        s3_key = f"deployments/{EB_APPLICATION_NAME}/{version_label}/Dockerrun.aws.json"
        upload_to_s3(dockerrun_json, s3_key)
        print()
        
        # 4. Crea application version
        print("🔨 Step 4: Creazione application version")
        create_application_version(version_label, s3_key)
        print()
        
        # 5. Deploy su environment
        print("🚀 Step 5: Deploy su environment")
        deploy_to_environment(version_label)
        print()
        
        # 6. Attendi completamento
        success = wait_for_environment_ready()
        
        if success:
            print("\n" + "="*70)
            print("✅ DEPLOY COMPLETATO CON SUCCESSO!")
            print("="*70)
        else:
            print("\n" + "="*70)
            print("⚠️  DEPLOY COMPLETATO MA CON WARNINGS")
            print("Controlla la console AWS Elastic Beanstalk per i dettagli")
            print("="*70)
        
    except Exception as e:
        print("\n" + "="*70)
        print("❌ DEPLOY FALLITO")
        print("="*70)
        print(f"Errore: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())