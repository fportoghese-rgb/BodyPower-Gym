import boto3
from botocore.exceptions import ClientError, NoCredentialsError

def test_aws_connection():
    """Testa la connessione AWS e verifica i permessi"""
    print("🔍 Testando connessione AWS...")
    
    try:
        # Test connessione base
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        
        print(f"✅ Connesso come: {identity.get('Arn', 'N/A')}")
        print(f"✅ Account ID: {identity['Account']}")
        print(f"✅ User ID: {identity['UserId']}")
        
        # Test accesso ai servizi necessari
        services_to_test = [
            ('codecommit', 'CodeCommit'),
            ('codepipeline', 'CodePipeline'), 
            ('codebuild', 'CodeBuild'),
            ('iam', 'IAM'),
            ('s3', 'S3'),
            ('lambda', 'Lambda')
        ]
        
        print("\n🔍 Testando accesso ai servizi...")
        for service_name, display_name in services_to_test:
            try:
                client = boto3.client(service_name, region_name='eu-west-1')
                if service_name == 'codecommit':
                    client.list_repositories()
                elif service_name == 'codepipeline':
                    client.list_pipelines()
                elif service_name == 'codebuild':
                    client.list_projects()
                elif service_name == 'iam':
                    client.list_roles()
                elif service_name == 's3':
                    client.list_buckets()
                elif service_name == 'lambda':
                    client.list_functions()
                    
                print(f"✅ {display_name}: OK")
            except ClientError as e:
                if e.response['Error']['Code'] in ['AccessDenied', 'UnauthorizedOperation']:
                    print(f"⚠️  {display_name}: Accesso limitato (potrebbero servire più permessi)")
                else:
                    print(f"❌ {display_name}: Errore - {e.response['Error']['Code']}")
            except Exception as e:
                print(f"❌ {display_name}: Errore - {str(e)}")
        
        return True
        
    except NoCredentialsError:
        print("❌ Credenziali AWS non configurate!")
        print("Esegui: aws configure")
        return False
    except Exception as e:
        print(f"❌ Errore di connessione: {str(e)}")
        return False

def check_existing_resources():
    """Controlla se esistono già risorse con nomi simili"""
    print("\n🔍 Controllando risorse esistenti...")
    
    try:
        # Controlla repository CodeCommit
        codecommit = boto3.client('codecommit', region_name='eu-west-1')
        repos = codecommit.list_repositories()
        if repos['repositories']:
            print("📦 Repository CodeCommit esistenti:")
            for repo in repos['repositories']:
                print(f"  - {repo['repositoryName']}")
        else:
            print("📦 Nessun repository CodeCommit trovato")
        
        # Controlla pipeline
        codepipeline = boto3.client('codepipeline', region_name='eu-west-1')
        pipelines = codepipeline.list_pipelines()
        if pipelines['pipelines']:
            print("🔄 Pipeline esistenti:")
            for pipeline in pipelines['pipelines']:
                print(f"  - {pipeline['name']}")
        else:
            print("🔄 Nessuna pipeline trovata")
            
        # Controlla progetti CodeBuild
        codebuild = boto3.client('codebuild', region_name='eu-west-1')
        projects = codebuild.list_projects()
        if projects['projects']:
            print("🔨 Progetti CodeBuild esistenti:")
            for project in projects['projects']:
                print(f"  - {project}")
        else:
            print("🔨 Nessun progetto CodeBuild trovato")
            
    except Exception as e:
        print(f"⚠️  Errore nel controllo risorse: {str(e)}")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 AWS CI/CD SETUP - TEST PRELIMINARE")
    print("=" * 60)
    
    if test_aws_connection():
        check_existing_resources()
        print("\n" + "=" * 60)
        print("✅ Test completato! Puoi procedere con il setup completo.")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ Risolvi i problemi di connessione prima di continuare.")
        print("=" * 60)