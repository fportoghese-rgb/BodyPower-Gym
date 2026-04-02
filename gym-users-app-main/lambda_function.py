
import json
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    print(f"Evento ricevuto: {json.dumps(event)}")
    
    try:
        # Logica della tua applicazione
        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'GymApp API - Request processed successfully',
                'timestamp': datetime.now().isoformat(),
                'data': event
            })
        }
        
        return response
        
    except Exception as e:
        print(f"Errore: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
