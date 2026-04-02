import boto3
import time
from botocore.exceptions import ClientError

def create_dynamodb_table():
    # Inizializza il client DynamoDB
    dynamodb = boto3.resource('dynamodb')
    
    table_name = 'gymcloudUsers'
    
    try:
        # Verifica se la tabella esiste già
        try:
            table = dynamodb.Table(table_name)
            table.meta.client.describe_table(TableName=table_name)
            print(f"Tabella {table_name} esiste già")
            return table
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise e
        
        # Crea la tabella DynamoDB
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'userId',
                    'KeyType': 'HASH'  # Chiave di partizione
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'userId',
                    'AttributeType': 'S'  # String
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand billing per GET e POST
        )
        
        print(f"Creazione tabella {table_name} in corso...")
        
        # Attendi che la tabella sia attiva
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        print(f"Tabella {table_name} creata con successo!")
        
        # Verifica lo stato della tabella
        response = table.meta.client.describe_table(TableName=table_name)
        table_status = response['Table']['TableStatus']
        print(f"Stato tabella: {table_status}")
        
        # Informazioni sulla tabella
        print(f"Nome tabella: {response['Table']['TableName']}")
        print(f"Chiave di partizione: {response['Table']['KeySchema'][0]['AttributeName']}")
        print(f"Modalità di fatturazione: {response['Table']['BillingModeSummary']['BillingMode']}")
        print(f"ARN tabella: {response['Table']['TableArn']}")
        
        return table
        
    except ClientError as e:
        print(f"Errore durante la creazione della tabella: {e}")
        return None
    except Exception as e:
        print(f"Errore generico: {e}")
        return None

def test_table_operations(table):
    """
    Test di operazioni GET e POST sulla tabella
    """
    if not table:
        print("Tabella non disponibile per i test")
        return
    
    try:
        # Test POST (PUT) - Inserimento di un elemento
        print("\nTest operazione POST (inserimento)...")
        table.put_item(
            Item={
                'userId': 'test-user-001',
                'name': 'Mario Rossi',
                'email': 'mario.rossi@email.com',
                'createdAt': int(time.time())
            }
        )
        print("Elemento inserito con successo")
        
        # Test GET - Lettura dell'elemento
        print("\nTest operazione GET (lettura)...")
        response = table.get_item(
            Key={
                'userId': 'test-user-001'
            }
        )
        
        if 'Item' in response:
            print("Elemento trovato:")
            for key, value in response['Item'].items():
                print(f"  {key}: {value}")
        else:
            print("Elemento non trovato")
            
    except ClientError as e:
        print(f"Errore durante i test: {e}")

if __name__ == "__main__":
    # Crea la tabella
    table = create_dynamodb_table()
    
    # Esegui test opzionali
    if table:
        print("\n" + "="*50)
        print("ESECUZIONE TEST OPERAZIONI")
        print("="*50)
        test_table_operations(table)    