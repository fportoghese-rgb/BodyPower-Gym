import boto3
import json
from botocore.exceptions import ClientError

def create_s3_bucket_for_website():
    # Inizializza il client S3
    s3_client = boto3.client('s3')
    
    bucket_name = 'gym-users-fronted'
    
    try:
        # Ottieni la regione corrente del client
        region = s3_client.meta.region_name
        
        # Verifica se il bucket esiste già
        try:
            s3_client.head_bucket(Bucket=bucket_name)
            print(f"Bucket {bucket_name} esiste già, procedo con la configurazione")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Il bucket non esiste, crealo
                if region == 'us-east-1':
                    s3_client.create_bucket(Bucket=bucket_name)
                else:
                    s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': region}
                    )
                print(f"Bucket {bucket_name} creato con successo nella regione {region}")
            else:
                raise e
        
        # Configura il bucket per hosting di sito web statico
        website_configuration = {
            'IndexDocument': {
                'Suffix': 'index.html'
            },
            'ErrorDocument': {
                'Key': 'error.html'
            }
        }
        
        s3_client.put_bucket_website(
            Bucket=bucket_name,
            WebsiteConfiguration=website_configuration
        )
        print("Configurazione hosting web applicata")
        
        # Configura CORS per permettere richieste GET e POST
        cors_configuration = {
            'CORSRules': [
                {
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['GET', 'POST'],
                    'AllowedOrigins': ['*'],
                    'ExposeHeaders': [],
                    'MaxAgeSeconds': 3600
                }
            ]
        }
        
        s3_client.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration=cors_configuration
        )
        print("Configurazione CORS applicata")
        
        # Configura policy per accesso pubblico in lettura (necessario per hosting web)
        bucket_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/*"
                }
            ]
        }
        
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(bucket_policy)
        )
        print("Policy di accesso pubblico applicata")
        
        # Disabilita il block public access per permettere l'hosting web
        s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': False,
                'IgnorePublicAcls': False,
                'BlockPublicPolicy': False,
                'RestrictPublicBuckets': False
            }
        )
        print("Accesso pubblico configurato")
        
        print(f"\nBucket {bucket_name} configurato correttamente per hosting web con CORS abilitato")
        
        # Genera l'URL corretto basato sulla regione
        if region == 'us-east-1':
            website_url = f"http://{bucket_name}.s3-website-us-east-1.amazonaws.com"
        else:
            website_url = f"http://{bucket_name}.s3-website-{region}.amazonaws.com"
            
        print(f"URL del sito web: {website_url}")
        
    except ClientError as e:
        print(f"Errore durante la creazione del bucket: {e}")
        return False
    
    return True

if __name__ == "__main__":
    create_s3_bucket_for_website()