import boto3
import json
import time
from botocore.exceptions import ClientError

class AWSResourceCreator:
    def __init__(self, region='eu-west-1'):
        self.region = region
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        
        # Inizializza i client AWS
        self.codecommit = boto3.client('codecommit', region_name=region)
        self.codepipeline = boto3.client('codepipeline', region_name=region)
        self.codebuild = boto3.client('codebuild', region_name=region)
        self.iam = boto3.client('iam', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        
        print(f"🌍 Regione: {region}")
        print(f"🆔 Account ID: {self.account_id}")
        print("-" * 50)

    def create_s3_bucket_for_artifacts(self, bucket_name):
        """Crea bucket S3 per gli artifacts della pipeline"""
        try:
            if self.region == 'us-east-1':
                # us-east-1 non ha bisogno di LocationConstraint
                self.s3.create_bucket(Bucket=bucket_name)
            else:
                self.s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region}
                )
            
            # Abilita versioning
            self.s3.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            print(f"✅ Bucket S3 {bucket_name} creato con successo!")
            return bucket_name
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                print(f"⚠️  Bucket {bucket_name} esiste già")
                return bucket_name
            else:
                print(f"❌ Errore creazione bucket: {e}")
                return None

    def create_codecommit_repo(self, repo_name):
        """Crea repository CodeCommit"""
        try:
            response = self.codecommit.create_repository(
                repositoryName=repo_name,
                repositoryDescription=f"Repository per {repo_name}"
            )
            
            clone_url_http = response['repositoryMetadata']['cloneUrlHttp']
            clone_url_ssh = response['repositoryMetadata']['cloneUrlSsh']
            
            print(f"✅ Repository CodeCommit creato!")
            print(f"   📍 Nome: {repo_name}")
            print(f"   🔗 Clone HTTPS: {clone_url_http}")
            print(f"   🔑 Clone SSH: {clone_url_ssh}")
            
            return {
                'name': repo_name,
                'cloneUrlHttp': clone_url_http,
                'cloneUrlSsh': clone_url_ssh
            }
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'RepositoryNameExistsException':
                print(f"⚠️  Repository {repo_name} esiste già")
                repo_info = self.codecommit.get_repository(repositoryName=repo_name)
                return {
                    'name': repo_name,
                    'cloneUrlHttp': repo_info['repositoryMetadata']['cloneUrlHttp'],
                    'cloneUrlSsh': repo_info['repositoryMetadata']['cloneUrlSsh']
                }
            else:
                print(f"❌ Errore creazione repository: {e}")
                return None

    def create_iam_role(self, role_name, trust_policy, managed_policies):
        """Crea ruolo IAM con policy"""
        try:
            # Crea ruolo
            response = self.iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f"Ruolo per {role_name}"
            )
            
            role_arn = response['Role']['Arn']
            
            # Attacca policy gestite
            for policy_arn in managed_policies:
                self.iam.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy_arn
                )
            
            print(f"✅ Ruolo IAM {role_name} creato!")
            print(f"   🔐 ARN: {role_arn}")
            return role_arn
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExistsException':
                print(f"⚠️  Ruolo {role_name} esiste già")
                role_info = self.iam.get_role(RoleName=role_name)
                return role_info['Role']['Arn']
            else:
                print(f"❌ Errore creazione ruolo: {e}")
                return None

    def create_codebuild_project(self, project_name, repo_name, ecr_repo_name, role_arn):
        """Crea progetto CodeBuild"""
        buildspec_content = {
            "version": "0.2",
            "phases": {
                "pre_build": {
                    "commands": [
                        "echo Logging in to Amazon ECR...",
                        f"aws ecr get-login-password --region {self.region} | docker login --username AWS --password-stdin {self.account_id}.dkr.ecr.{self.region}.amazonaws.com"
                    ]
                },
                "build": {
                    "commands": [
                        "echo Build started on `date`",
                        "echo Building the Docker image...",
                        f"docker build -t {ecr_repo_name}:$CODEBUILD_RESOLVED_SOURCE_VERSION .",
                        f"docker tag {ecr_repo_name}:$CODEBUILD_RESOLVED_SOURCE_VERSION {self.account_id}.dkr.ecr.{self.region}.amazonaws.com/{ecr_repo_name}:latest"
                    ]
                },
                "post_build": {
                    "commands": [
                        "echo Build completed on `date`",
                        "echo Pushing the Docker image...",
                        f"docker push {self.account_id}.dkr.ecr.{self.region}.amazonaws.com/{ecr_repo_name}:latest",
                        "echo Writing image definitions file...",
                        f'printf \'[{{"name":"container","imageUri":"%s"}}]\' {self.account_id}.dkr.ecr.{self.region}.amazonaws.com/{ecr_repo_name}:latest > imagedefinitions.json'
                    ]
                }
            },
            "artifacts": {
                "files": [
                    "imagedefinitions.json"
                ]
            }
        }
        
        try:
            response = self.codebuild.create_project(
                name=project_name,
                source={
                    'type': 'CODECOMMIT',
                    'location': f"https://git-codecommit.{self.region}.amazonaws.com/v1/repos/{repo_name}",
                    'buildspec': json.dumps(buildspec_content, indent=2)
                },
                artifacts={
                    'type': 'CODEPIPELINE'
                },
                environment={
                    'type': 'LINUX_CONTAINER',
                    'image': 'aws/codebuild/standard:7.0',
                    'computeType': 'BUILD_GENERAL1_MEDIUM',
                    'privilegedMode': True
                },
                serviceRole=role_arn
            )
            
            print(f"✅ Progetto CodeBuild creato!")
            print(f"   🔨 Nome: {project_name}")
            return project_name
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                print(f"⚠️  Progetto {project_name} esiste già")
                return project_name
            else:
                print(f"❌ Errore creazione progetto CodeBuild: {e}")
                return None

    def create_pipeline(self, pipeline_name, repo_name, build_project, bucket_name, lambda_function_name, role_arn):
        """Crea pipeline CodePipeline"""
        pipeline_definition = {
            "name": pipeline_name,
            "roleArn": role_arn,
            "artifactStore": {
                "type": "S3",
                "location": bucket_name
            },
            "stages": [
                {
                    "name": "Source",
                    "actions": [
                        {
                            "name": "SourceAction",
                            "actionTypeId": {
                                "category": "Source",
                                "owner": "AWS",
                                "provider": "CodeCommit",
                                "version": "1"
                            },
                            "configuration": {
                                "RepositoryName": repo_name,
                                "BranchName": "main"
                            },
                            "outputArtifacts": [{"name": "SourceOutput"}]
                        }
                    ]
                },
                {
                    "name": "Build",
                    "actions": [
                        {
                            "name": "BuildAction",
                            "actionTypeId": {
                                "category": "Build",
                                "owner": "AWS",
                                "provider": "CodeBuild",
                                "version": "1"
                            },
                            "configuration": {
                                "ProjectName": build_project
                            },
                            "inputArtifacts": [{"name": "SourceOutput"}],
                            "outputArtifacts": [{"name": "BuildOutput"}]
                        }
                    ]
                }
            ]
        }
        
        try:
            response = self.codepipeline.create_pipeline(pipeline=pipeline_definition)
            
            print(f"✅ Pipeline CodePipeline creata!")
            print(f"   🔄 Nome: {pipeline_name}")
            return pipeline_name
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'PipelineNameInUseException':
                print(f"⚠️  Pipeline {pipeline_name} esiste già")
                return pipeline_name
            else:
                print(f"❌ Errore creazione pipeline: {e}")
                return None

def sanitize_name(name):
    """Pulisce il nome per renderlo compatibile con AWS"""
    # Converti in lowercase
    clean_name = name.lower()
    
    # Sostituisci spazi e caratteri non validi con trattini
    import re
    clean_name = re.sub(r'[^a-zA-Z0-9._-]', '-', clean_name)
    
    # Rimuovi trattini multipli
    clean_name = re.sub(r'-+', '-', clean_name)
    
    # Rimuovi trattini all'inizio e alla fine
    clean_name = clean_name.strip('-')
    
    # Assicurati che non sia vuoto
    if not clean_name:
        clean_name = "progetto-aws"
    
    return clean_name

def main():
    print("🚀 CREAZIONE RISORSE AWS PER CI/CD")
    print("=" * 50)
    
    # Chiedi nome progetto
    user_input = input("📝 Inserisci il nome del progetto (es: mio-progetto): ").strip()
    if not user_input:
        user_input = "mio-progetto-aws"
    
    # Pulisci il nome per AWS
    project_name = sanitize_name(user_input)
    
    print(f"\n🎯 Nome progetto originale: {user_input}")
    print(f"🔧 Nome progetto AWS-compatibile: {project_name}")
    print("-" * 50)
    
    # Inizializza creator
    creator = AWSResourceCreator()
    
    # Nomi delle risorse
    repo_name = f"{project_name}-repo"
    bucket_name = f"pipeline-artifacts-{creator.account_id}-{creator.region}"
    codebuild_role_name = f"{project_name}-codebuild-role"
    pipeline_role_name = f"{project_name}-pipeline-role"
    build_project_name = f"{project_name}-build"
    pipeline_name = f"{project_name}-pipeline"
    ecr_repo_name = f"{project_name}-ecr"
    lambda_function_name = f"{project_name}-lambda"
    
    success = True
    
    # 1. Crea bucket S3 per artifacts
    print("\n1️⃣ Creando bucket S3 per artifacts...")
    bucket_result = creator.create_s3_bucket_for_artifacts(bucket_name)
    if not bucket_result:
        success = False
    
    # 2. Crea repository CodeCommit
    print("\n2️⃣ Creando repository CodeCommit...")
    repo_result = creator.create_codecommit_repo(repo_name)
    if not repo_result:
        success = False
    
    # 3. Crea ruoli IAM
    print("\n3️⃣ Creando ruoli IAM...")
    
    # Ruolo CodeBuild
    codebuild_trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "codebuild.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    codebuild_policies = [
        "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser",
        "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
    ]
    
    codebuild_role_arn = creator.create_iam_role(
        codebuild_role_name,
        codebuild_trust_policy,
        codebuild_policies
    )
    
    if not codebuild_role_arn:
        success = False
    
    # Ruolo CodePipeline
    pipeline_trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "codepipeline.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    pipeline_policies = [
        "arn:aws:iam::aws:policy/AWSCodePipelineServiceRole",
        "arn:aws:iam::aws:policy/AWSCodeCommitReadOnly",
        "arn:aws:iam::aws:policy/AWSCodeBuildDeveloperAccess",
        "arn:aws:iam::aws:policy/AmazonS3FullAccess"
    ]
    
    pipeline_role_arn = creator.create_iam_role(
        pipeline_role_name,
        pipeline_trust_policy,
        pipeline_policies
    )
    
    if not pipeline_role_arn:
        success = False
    
    if not success:
        print("\n❌ Errori nella creazione dei ruoli. Fermiamo qui.")
        return
    
    # Aspetta propagazione ruoli
    print("\n⏳ Attendendo propagazione ruoli IAM (30 secondi)...")
    time.sleep(30)
    
    # 4. Crea progetto CodeBuild
    print("\n4️⃣ Creando progetto CodeBuild...")
    build_result = creator.create_codebuild_project(
        build_project_name,
        repo_name,
        ecr_repo_name,
        codebuild_role_arn
    )
    
    if not build_result:
        success = False
    
    # 5. Crea pipeline
    print("\n5️⃣ Creando pipeline CodePipeline...")
    pipeline_result = creator.create_pipeline(
        pipeline_name,
        repo_name,
        build_project_name,
        bucket_name,
        lambda_function_name,
        pipeline_role_arn
    )
    
    if not pipeline_result:
        success = False
    
    # Risultato finale
    print("\n" + "=" * 60)
    if success:
        print("🎉 SETUP COMPLETATO CON SUCCESSO!")
        print("=" * 60)
        print(f"📦 Repository CodeCommit: {repo_name}")
        print(f"🔨 Progetto CodeBuild: {build_project_name}")
        print(f"🔄 Pipeline: {pipeline_name}")
        print(f"🪣 Bucket artifacts: {bucket_name}")
        
        if repo_result:
            print(f"\n📋 PROSSIMI PASSI:")
            print("1️⃣ Clona il repository:")
            print(f"   git clone {repo_result['cloneUrlHttp']}")
            print("2️⃣ Aggiungi i file del progetto")
            print("3️⃣ Commit e push per avviare la pipeline")
    else:
        print("❌ SETUP NON COMPLETATO - Ci sono stati degli errori")
    
    print("=" * 60)

if __name__ == "__main__":
    main()