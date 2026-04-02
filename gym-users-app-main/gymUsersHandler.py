import json
import os
import re
import uuid
import datetime
import logging
import boto3
from botocore.exceptions import ClientError

# Configura il logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configura il client DynamoDB
TABLE_NAME = "gymcloudUsers"
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
table = dynamodb.Table(TABLE_NAME)

# Funzione helper per risposte CORS
def create_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
        },
        'body': json.dumps(body, default=str),  # default=str gestisce oggetti come datetime
    }

# Funzione per generare UUID
def generate_uuid():
    return str(uuid.uuid4())

# Validazione email
def is_valid_email(email):
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    return re.match(email_regex, email)

# Validazione telefono italiano
def is_valid_phone(phone):
    phone_regex = r'^(\+39)?[0-9]{10}$'
    return re.match(phone_regex, re.sub(r'\s+', '', phone))

# Funzione helper per calcolare data fine abbonamento
def calculate_membership_end_date(subscription_type):
    start_date = datetime.date.today()
    end_date = start_date
    
    if subscription_type == 'monthly':
        end_date = start_date + datetime.timedelta(days=30)
    elif subscription_type == 'quarterly':
        end_date = start_date + datetime.timedelta(days=90)
    elif subscription_type == 'yearly' or subscription_type == 'premium':
        end_date = start_date + datetime.timedelta(days=365)
    else:
        end_date = start_date + datetime.timedelta(days=30) # Default 1 mese

    return end_date.isoformat()

# GET /users - Recupera tutti gli utenti
def get_users():
    try:
        logger.info("Getting all users from table: %s", TABLE_NAME)
        
        response = table.scan()
        users = response.get('Items', [])
        
        logger.info("Found %d users", len(users))
        
        return create_response(200, {
            "success": True,
            "members": users,
            "total": len(users)
        })
    except ClientError as e:
        logger.error("Error getting users: %s", e)
        return create_response(500, {
            "success": False,
            "error": "Failed to retrieve users",
            "details": str(e)
        })

# POST /users - Crea nuovo utente con dati dal frontend
def create_user(user_data):
    try:
        logger.info("Creating user with data: %s", json.dumps(user_data, indent=2))
        
        # Validazione dati obbligatori
        if not user_data.get('name') or not user_data.get('email'):
            return create_response(400, {
                "success": False,
                "error": "Nome e email sono obbligatori"
            })
            
        # Validazione email
        if not is_valid_email(user_data['email']):
            return create_response(400, {
                "success": False,
                "error": "Formato email non valido"
            })

        # Validazione telefono (se fornito)
        if user_data.get('phone') and not is_valid_phone(user_data['phone']):
            return create_response(400, {
                "success": False,
                "error": "Formato telefono non valido"
            })

        # Verifica se email già esistente
        response = table.scan(
            FilterExpression="email = :email",
            ExpressionAttributeValues={
                ":email": user_data['email'].lower()
            }
        )
        if response.get('Items') and len(response['Items']) > 0:
            return create_response(409, {
                "success": False,
                "error": "Un utente con questa email esiste già"
            })

        # Dividi nome completo in nome e cognome
        name_parts = user_data['name'].strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Crea oggetto utente per DynamoDB
        new_user = {
            'userId': generate_uuid(),
            'firstName': first_name,
            'lastName': last_name,
            'fullName': user_data['name'].strip(),
            'email': user_data['email'].lower(),
            'phone': re.sub(r'\s+', '', user_data.get('phone', '')),
            'membershipType': user_data.get('subscriptionType', 'basic'),
            'membershipStartDate': datetime.date.today().isoformat(),
            'membershipEndDate': calculate_membership_end_date(user_data.get('subscriptionType')),
            'status': user_data.get('status', 'active'),
            'isActive': True,
            'createdAt': datetime.datetime.utcnow().isoformat(),
            'updatedAt': datetime.datetime.utcnow().isoformat(),
            
            # Campi opzionali
            'birthDate': user_data.get('birthDate', ''),
            'goal': user_data.get('goal', 'Mantenersi in forma'),
            
            'address': user_data.get('address', {
                'street': '', 'city': '', 'zipCode': ''
            }),
            
            'emergencyContact': user_data.get('emergencyContact', {
                'name': '', 'phone': '', 'relationship': ''
            }),
            
            'medicalInfo': user_data.get('medicalInfo', {
                'allergies': 'Nessuna', 'conditions': 'Nessuna'
            })
        }
        
        # Salva nel database
        table.put_item(Item=new_user)
        logger.info("User created successfully: %s", new_user['userId'])

        return create_response(201, {
            "success": True,
            "message": f"Membro \"{user_data['name']}\" creato con successo",
            "user": new_user,
            "id": new_user['userId']
        })

    except Exception as e:
        logger.error("Error creating user: %s", e)
        return create_response(500, {
            "success": False,
            "error": "Errore nella creazione dell'utente",
            "details": str(e)
        })

# DELETE /users/{id} - Elimina utente
def delete_user(user_id):
    try:
        logger.info("Deleting user: %s", user_id)
        
        # Verifica se l'utente esiste
        response = table.get_item(Key={'userId': user_id})
        if 'Item' not in response:
            return create_response(404, {
                "success": False,
                "error": "Utente non trovato"
            })
            
        # Elimina l'utente
        table.delete_item(Key={'userId': user_id})
        logger.info("User deleted successfully: %s", user_id)

        return create_response(200, {
            "success": True,
            "message": "Utente eliminato con successo",
            "deletedUserId": user_id
        })
        
    except ClientError as e:
        logger.error("Error deleting user: %s", e)
        return create_response(500, {
            "success": False,
            "error": "Errore nell'eliminazione dell'utente",
            "details": str(e)
        })

# GET /stats - Statistiche palestra
def get_stats():
    try:
        logger.info("Getting gym statistics")
        
        response = table.scan()
        users = response.get('Items', [])
        
        today = datetime.date.today().isoformat()
        new_members_today = len([user for user in users if user.get('createdAt', '').startswith(today)])
        active_members = len([user for user in users if user.get('isActive')])
        
        # Raggruppa per tipo di abbonamento
        membership_types = {
            'monthly': 0, 'quarterly': 0, 'yearly': 0, 'basic': 0, 'premium': 0
        }
        for user in users:
            membership_type = user.get('membershipType', 'basic')
            if membership_type in membership_types:
                membership_types[membership_type] += 1
        
        stats = {
            'totalMembers': len(users),
            'newMembersToday': new_members_today,
            'activeMembers': active_members,
            'activeSubscriptions': len([u for u in users if u.get('membershipType') and u.get('membershipType') != 'inactive']),
            'membershipTypes': membership_types
        }

        return create_response(200, {
            "success": True,
            "stats": stats
        })
    except Exception as e:
        logger.error("Error getting stats: %s", e)
        return create_response(500, {
            "success": False,
            "error": "Errore nel recupero delle statistiche",
            "details": str(e)
        })

# Handler principale
def handler(event, context):
    try:
        logger.info("=== LAMBDA EXECUTION START ===")
        logger.info("Full event received: %s", json.dumps(event, indent=2))
        
        http_method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method')
        path = event.get('path') or event.get('requestContext', {}).get('http', {}).get('path')
        
        if not http_method or not path:
            return create_response(400, {"success": False, "error": "Invalid request"})

        # Pulisci il path
        path = re.sub(r'/+', '/', path)
        if path.endswith('/') and len(path) > 1:
            path = path[:-1]

        logger.info("Processing: %s %s", http_method, path)

        # Gestisci richieste CORS preflight
        if http_method == "OPTIONS":
            logger.info("CORS preflight request")
            return create_response(200, {"message": "CORS preflight successful"})
            
        # =====================
        # GESTIONE DEI ROUTE
        # =====================

        # GET /users
        if http_method == "GET" and (path == "/users" or path == "/members"):
            logger.info("Route: GET users")
            return get_users()

        # GET /stats
        if http_method == "GET" and path == "/stats":
            logger.info("Route: GET stats")
            return get_stats()

        # POST /users
        if http_method == "POST" and (path == "/users" or path == "/members"):
            logger.info("Route: POST users")
            user_data = {}
            if event.get('body'):
                try:
                    user_data = json.loads(event['body'])
                except json.JSONDecodeError:
                    return create_response(400, {"success": False, "error": "Invalid JSON in request body"})
            return create_user(user_data)

        # DELETE /users/{id}
        if http_method == "DELETE" and path.startswith("/users/"):
            user_id = path.split('/')[2]
            logger.info("Route: DELETE user %s", user_id)
            if not user_id:
                return create_response(400, {"success": False, "error": "User ID is required"})
            return delete_user(user_id)

        # Route non trovata
        logger.info("Route not found: %s %s", http_method, path)
        return create_response(404, {
            "success": False,
            "error": "Endpoint not found",
            "availableEndpoints": [
                "GET /users - Lista membri",
                "POST /users - Crea membro",
                "DELETE /users/{id} - Elimina membro",
                "GET /stats - Statistiche"
            ]
        })

    except Exception as e:
        logger.error("=== LAMBDA EXECUTION ERROR ===")
        logger.error("Error: %s", e)
        logger.error("Stack:", exc_info=True)
        return create_response(500, {
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        })
    finally:
        logger.info("=== LAMBDA EXECUTION END ===")