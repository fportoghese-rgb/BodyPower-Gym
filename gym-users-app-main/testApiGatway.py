import boto3
import json
import time
import zipfile
import os
from botocore.exceptions import ClientError

# Nome del file sorgente della tua Lambda
LAMBDA_SOURCE_FILE = 'gymUsersHandler.py'
LAMBDA_FUNCTION_NAME = 'gymUsersHandler'
LAMBDA_ROLE_NAME = 'gymUsersLambdaRole'

REGION = 'us-east-1'

def create_lambda_function():
    """
    Crea un pacchetto .zip dal codice locale, crea un ruolo IAM
    e deploya la funzione Lambda su AWS.
    """
    print("Creazione pacchetto di deployment...")
    zip_file_name = 'lambda_package.zip'
    with zipfile.ZipFile(zip_file_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(LAMBDA_SOURCE_FILE, os.path.basename(LAMBDA_SOURCE_FILE))

    lambda_client = boto3.client('lambda')
    iam_client = boto3.client('iam')
    account_id = boto3.client('sts').get_caller_identity()['Account']
    region = boto3.Session().region_name

    try:
        # Crea o ottieni un ruolo IAM per la Lambda
        print("Creazione o recupero ruolo IAM per Lambda...")
        role_arn = create_or_get_iam_role(iam_client, LAMBDA_ROLE_NAME)
        
        # Attendi che il ruolo sia propagato
        time.sleep(10)

        # Cerca se la funzione Lambda esiste già per aggiornarla
        try:
            lambda_client.get_function(FunctionName=LAMBDA_FUNCTION_NAME)
            print(f"Funzione Lambda '{LAMBDA_FUNCTION_NAME}' esistente. Aggiornamento del codice...")
            response = lambda_client.update_function_code(
                FunctionName=LAMBDA_FUNCTION_NAME,
                ZipFile=open(zip_file_name, 'rb').read()
            )
            lambda_arn = response['FunctionArn']

        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"Creazione della funzione Lambda '{LAMBDA_FUNCTION_NAME}'...")
                response = lambda_client.create_function(
                    FunctionName=LAMBDA_FUNCTION_NAME,
                    Runtime='python3.9',
                    Role=role_arn,
                    Handler=f"{os.path.splitext(os.path.basename(LAMBDA_SOURCE_FILE))[0]}.handler",
                    Code={
                        'ZipFile': open(zip_file_name, 'rb').read()
                    },
                    Timeout=30,
                    MemorySize=128
                )
                lambda_arn = response['FunctionArn']
            else:
                raise e

        # Rimuovi il file zip
        os.remove(zip_file_name)
        
        print(f"Lambda Function creata/aggiornata con successo. ARN: {lambda_arn}")
        return lambda_arn

    except ClientError as e:
        print(f"Errore nel deployment della Lambda: {e}")
        return None

def create_or_get_iam_role(iam_client, role_name):
    """Crea un ruolo IAM se non esiste e restituisce l'ARN."""
    try:
        role = iam_client.get_role(RoleName=role_name)
        print(f"Ruolo IAM '{role_name}' trovato.")
        return role['Role']['Arn']
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchEntity':
            print(f"Ruolo IAM '{role_name}' non trovato. Creazione...")
            assume_role_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
            create_role_response = iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy),
                Description='Ruolo per la funzione Lambda di gestione utenti'
            )
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
            )
            # Aggiungi permessi per DynamoDB e S3
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn='arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess'
            )
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess'
            )
            return create_role_response['Role']['Arn']
        else:
            raise e

def create_api_gateway():
    """
    Crea l'API Gateway, le risorse e le integra con la Lambda.
    """
    # Inizializza i client
    apigateway = boto3.client('apigateway')
    lambda_client = boto3.client('lambda')
    
    api_name = 'gym-users-api'
    
    try:
        # 1. Deployment della Lambda Function prima di tutto
        lambda_arn = create_lambda_function()
        if not lambda_arn:
            print("Fallito il deployment della Lambda. API Gateway non creato.")
            return None
            
        # 2. Crea API Gateway REST API
        print("Creazione API Gateway...")
        # ... (il resto del codice rimane invariato, dalla riga 10 in poi)
        api_response = apigateway.create_rest_api(
            name=api_name,
            description='API per gestione utenti gym - comunicazione tra S3 e DynamoDB',
            endpointConfiguration={
                'types': ['REGIONAL']
            }
        )
        
        api_id = api_response['id']
        print(f"API Gateway creato con ID: {api_id}")
        
        # 3. Ottieni il root resource ID
        resources = apigateway.get_resources(restApiId=api_id)
        root_resource_id = None
        for resource in resources['items']:
            if resource['path'] == '/':
                root_resource_id = resource['id']
                break
        
        # 4. Crea risorsa /users
        print("Creazione risorsa /users...")
        users_resource = apigateway.create_resource(
            restApiId=api_id,
            parentId=root_resource_id,
            pathPart='users'
        )
        users_resource_id = users_resource['id']
        
        # 5. Abilita CORS per la risorsa /users
        enable_cors(apigateway, api_id, users_resource_id)
        
        # 6. Crea metodo GET per /users (leggere tutti gli utenti)
        print("Creazione metodo GET /users...")
        apigateway.put_method(
            restApiId=api_id,
            resourceId=users_resource_id,
            httpMethod='GET',
            authorizationType='NONE',
            requestParameters={}
        )
        
        # 7. Crea metodo POST per /users (creare nuovo utente)
        print("Creazione metodo POST /users...")
        apigateway.put_method(
            restApiId=api_id,
            resourceId=users_resource_id,
            httpMethod='POST',
            authorizationType='NONE',
            requestParameters={}
        )
        
        # 8. Integra GET con Lambda esistente
        setup_lambda_integration(apigateway, api_id, users_resource_id, 'GET', lambda_arn)
        
        # 9. Integra POST con Lambda esistente
        setup_lambda_integration(apigateway, api_id, users_resource_id, 'POST', lambda_arn)
        
        # 10. Crea risorsa /stats per le statistiche
        print("Creazione risorsa /stats...")
        stats_resource = apigateway.create_resource(
            restApiId=api_id,
            parentId=root_resource_id,
            pathPart='stats'
        )
        stats_resource_id = stats_resource['id']
        
        # Abilita CORS per /stats
        enable_cors(apigateway, api_id, stats_resource_id)
        
        # Crea metodo GET per /stats
        print("Creazione metodo GET /stats...")
        apigateway.put_method(
            restApiId=api_id,
            resourceId=stats_resource_id,
            httpMethod='GET',
            authorizationType='NONE',
            requestParameters={}
        )
        
        # Integra GET /stats con Lambda
        setup_lambda_integration(apigateway, api_id, stats_resource_id, 'GET', lambda_arn)
        
        # 11. Crea risorsa /users/{id} per DELETE
        print("Creazione risorsa /users/{id}...")
        user_id_resource = apigateway.create_resource(
            restApiId=api_id,
            parentId=users_resource_id,
            pathPart='{id}'
        )
        user_id_resource_id = user_id_resource['id']
        
        # Abilita CORS per /users/{id}
        enable_cors(apigateway, api_id, user_id_resource_id)
        
        # Crea metodo DELETE per /users/{id}
        print("Creazione metodo DELETE /users/{id}...")
        apigateway.put_method(
            restApiId=api_id,
            resourceId=user_id_resource_id,
            httpMethod='DELETE',
            authorizationType='NONE',
            requestParameters={
                'method.request.path.id': True
            }
        )
        
        # Integra DELETE con Lambda
        setup_lambda_integration(apigateway, api_id, user_id_resource_id, 'DELETE', lambda_arn)
        
        # 12. Aggiungi permessi Lambda per API Gateway
        add_lambda_permissions(lambda_client, LAMBDA_FUNCTION_NAME, api_id)
        
        # 13. Deploy API
        print("Deploy dell'API...")
        apigateway.create_deployment(
            restApiId=api_id,
            stageName='nuovafase',
            description='Production'
        )
        
        # 14. URL dell'API
        region = boto3.Session().region_name or 'us-east-1'
        api_url = f"https://{api_id}.execute-api.{region}.amazonaws.com/nuovafase"
        
        print(f"\n{'='*60}")
        print("API GATEWAY CREATO CON SUCCESSO!")
        print(f"{'='*60}")
        print(f"API ID: {api_id}")
        print(f"Base URL: {api_url}")
        print(f"GET Users: {api_url}/users")
        print(f"POST User: {api_url}/users") 
        print(f"DELETE User: {api_url}/users/{{id}}")
        print(f"GET Stats: {api_url}/stats")
        print(f"{'='*60}")
        
        return {
            'api_id': api_id,
            'api_url': api_url,
            'lambda_arn': lambda_arn
        }
        
    except ClientError as e:
        print(f"Errore durante la creazione dell'API Gateway: {e}")
        return None

def enable_cors(apigateway, api_id, resource_id):
    # Funzione per abilitare CORS (non modificata)
    # ...
    try:
        # Crea metodo OPTIONS per CORS
        apigateway.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            authorizationType='NONE'
        )
        
        # Integrazione MOCK per OPTIONS
        apigateway.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            type='MOCK',
            requestTemplates={
                'application/json': '{"statusCode": 200}'
            }
        )
        
        # Response per OPTIONS
        apigateway.put_method_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Origin': False,
                'method.response.header.Access-Control-Allow-Headers': False,
                'method.response.header.Access-Control-Allow-Methods': False
            }
        )
        
        # Integration response per OPTIONS
        apigateway.put_integration_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod='OPTIONS',
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Origin': "'*'",
                'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                'method.response.header.Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'"
            }
        )
        
        print(f"CORS configurato per la risorsa ID: {resource_id}")
        
    except ClientError as e:
        print(f"Errore nella configurazione CORS: {e}")

def setup_lambda_integration(apigateway, api_id, resource_id, http_method, lambda_arn):
    try:
        region = boto3.Session().region_name or 'us-east-1'
        lambda_uri = f"arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
        
        # Configura integrazione (non toccare questa parte)
        apigateway.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=http_method,
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=lambda_uri
        )
        
        # Configura la 'Method Response'
        apigateway.put_method_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=http_method,
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Origin': True # Imposta a True per permettere l'header
            }
        )
        
        # *** QUI STA LA CORREZIONE CHIAVE ***
        # Aggiungi un 'Integration Response' per mappare la risposta 200 della Lambda
        apigateway.put_integration_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=http_method,
            statusCode='200',
            responseParameters={
                'method.response.header.Access-Control-Allow-Origin': "'*'" # Imposta il valore dell'header a '*'
            }
        )
        
        print(f"Integrazione {http_method} configurata con successo, inclusa la risposta CORS.")
        
    except ClientError as e:
        print(f"Errore nella configurazione dell'integrazione {http_method}: {e}")
        
def add_lambda_permissions(lambda_client, function_name, api_id):
    # Funzione per aggiungere i permessi (non modificata)
    # ...
    try:
        account_id = boto3.client('sts').get_caller_identity()['Account']
        region = boto3.Session().region_name or 'us-east-1'
        
        source_arn = f"arn:aws:execute-api:{region}:{account_id}:{api_id}/*/*"
        
        lambda_client.add_permission(
            FunctionName=function_name,
            StatementId=f"api-gateway-{function_name}-{int(time.time())}",
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=source_arn
        )
        
        print(f"Permessi aggiunti per {function_name}")
        
    except ClientError as e:
        if e.response['Error']['Code'] != 'ResourceConflictException':
            print(f"Errore nell'aggiunta dei permessi per {function_name}: {e}")

if __name__ == "__main__":
    result = create_api_gateway()
    
    if result:
        print(f"\n🚀 SETUP COMPLETATO!")
        print(f"Ora puoi utilizzare l'API:")
        print(f"- GET {result['api_url']}/users (per leggere tutti gli utenti)")
        print(f"- POST {result['api_url']}/users (per creare un nuovo utente)")
        print(f"- DELETE {result['api_url']}/users/{{id}} (per eliminare un utente)")
        print(f"- GET {result['api_url']}/stats (per ottenere statistiche)")
        print(f"\nEsempio POST body:")
        print(json.dumps({
            "name": "Mario Rossi",
            "email": "mario@example.com",
            "phone": "+39 123 456 7890",
            "subscriptionType": "monthly",
            "goal": "Perdere peso"
        }, indent=2))