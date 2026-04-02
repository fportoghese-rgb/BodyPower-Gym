import boto3
import json
import time 

# Client AWS
iam = boto3.client("iam")
s3 = boto3.client("s3")
codepipeline = boto3.client("codepipeline")
codebuild = boto3.client("codebuild")

# Parametri principali
PIPELINE_ROLE_NAME = "gymcloud-pipeline-role"
CODEBUILD_ROLE_NAME = "gymcloud-codebuild-role"
PIPELINE_NAME = "gymcloud-pipeline"
ARTIFACT_BUCKET = "gym-users-fronted"
REGION = "us-east-1"
AWS_ACCOUNT_ID = "724201375649"

# PARAMETRI GITHUB
CODE_CONNECTION_ARN = "arn:aws:codeconnections:us-east-1:724201375649:connection/4456474c-2207-4002-916c-ff700e53165e" 
REPOSITORY_OWNER = "DarkCiccioM"
REPOSITORY_NAME = "gym-users-app"
BRANCH = "main"

CODEBUILD_PROJECT = "gymcloud-codebuild"


def ensure_codebuild_role():
    """Crea o aggiorna il ruolo IAM per CodeBuild con tutti i permessi necessari."""
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "codebuild.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }

    try:
        iam.get_role(RoleName=CODEBUILD_ROLE_NAME)
        print(f"✅ Ruolo CodeBuild {CODEBUILD_ROLE_NAME} già esistente")
        iam.update_assume_role_policy(
            RoleName=CODEBUILD_ROLE_NAME,
            PolicyDocument=json.dumps(trust_policy)
        )
    except iam.exceptions.NoSuchEntityException:
        print(f"🔨 Creo ruolo CodeBuild {CODEBUILD_ROLE_NAME}...")
        iam.create_role(
            RoleName=CODEBUILD_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Role per CodeBuild di GymCloud"
        )
        time.sleep(5)

    # Policy inline completa per CodeBuild
    codebuild_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                ],
                "Resource": [
                    f"arn:aws:logs:{REGION}:{AWS_ACCOUNT_ID}:log-group:/aws/codebuild/{CODEBUILD_PROJECT}",
                    f"arn:aws:logs:{REGION}:{AWS_ACCOUNT_ID}:log-group:/aws/codebuild/{CODEBUILD_PROJECT}:*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:GetObjectVersion",
                    "s3:GetBucketAcl",
                    "s3:GetBucketLocation",
                    "s3:ListBucket"
                ],
                "Resource": [
                    f"arn:aws:s3:::{ARTIFACT_BUCKET}",
                    f"arn:aws:s3:::{ARTIFACT_BUCKET}/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "codebuild:CreateReportGroup",
                    "codebuild:CreateReport",
                    "codebuild:UpdateReport",
                    "codebuild:BatchPutTestCases",
                    "codebuild:BatchPutCodeCoverages"
                ],
                "Resource": f"arn:aws:codebuild:{REGION}:{AWS_ACCOUNT_ID}:report-group/{CODEBUILD_PROJECT}-*"
            }
        ]
    }

    try:
        iam.put_role_policy(
            RoleName=CODEBUILD_ROLE_NAME,
            PolicyName="CodeBuildBasePolicy",
            PolicyDocument=json.dumps(codebuild_policy)
        )
        print("✅ Policy CodeBuild applicata")
    except Exception as e:
        print(f"❌ Errore policy CodeBuild: {e}")

    role = iam.get_role(RoleName=CODEBUILD_ROLE_NAME)
    return role["Role"]["Arn"]


def ensure_pipeline_role():
    """Crea o aggiorna il ruolo IAM per CodePipeline con TUTTI i permessi necessari."""
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "codepipeline.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }

    try:
        iam.get_role(RoleName=PIPELINE_ROLE_NAME)
        print(f"✅ Ruolo Pipeline {PIPELINE_ROLE_NAME} già esistente")
        iam.update_assume_role_policy(
            RoleName=PIPELINE_ROLE_NAME,
            PolicyDocument=json.dumps(trust_policy)
        )
    except iam.exceptions.NoSuchEntityException:
        print(f"🔨 Creo ruolo Pipeline {PIPELINE_ROLE_NAME}...")
        iam.create_role(
            RoleName=PIPELINE_ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description="Role per CodePipeline di GymCloud"
        )
        time.sleep(5)

    # Policy inline COMPLETA per CodePipeline
    pipeline_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "codeconnections:UseConnection",
                    "codestar-connections:UseConnection"
                ],
                "Resource": CODE_CONNECTION_ARN
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:GetObjectVersion",
                    "s3:GetBucketVersioning",
                    "s3:PutObject",
                    "s3:PutObjectAcl",
                    "s3:ListBucket"
                ],
                "Resource": [
                    f"arn:aws:s3:::{ARTIFACT_BUCKET}",
                    f"arn:aws:s3:::{ARTIFACT_BUCKET}/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "codebuild:BatchGetBuilds",
                    "codebuild:StartBuild",
                    "codebuild:StopBuild"
                ],
                "Resource": f"arn:aws:codebuild:{REGION}:{AWS_ACCOUNT_ID}:project/{CODEBUILD_PROJECT}"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "iam:PassRole"
                ],
                "Resource": "*",
                "Condition": {
                    "StringEqualsIfExists": {
                        "iam:PassedToService": [
                            "codebuild.amazonaws.com"
                        ]
                    }
                }
            }
        ]
    }

    try:
        iam.put_role_policy(
            RoleName=PIPELINE_ROLE_NAME,
            PolicyName="CodePipelineFullPolicy",
            PolicyDocument=json.dumps(pipeline_policy)
        )
        print("✅ Policy Pipeline applicata")
        print("⏳ Attendo 20 secondi per la propagazione IAM...")
        time.sleep(20)
    except Exception as e:
        print(f"❌ Errore policy Pipeline: {e}")

    role = iam.get_role(RoleName=PIPELINE_ROLE_NAME)
    return role["Role"]["Arn"]


def ensure_bucket():
    """Verifica o crea il bucket S3 per gli artifacts."""
    try:
        s3.head_bucket(Bucket=ARTIFACT_BUCKET)
        print(f"✅ Bucket {ARTIFACT_BUCKET} esistente")
    except:
        print(f"🔨 Creo bucket {ARTIFACT_BUCKET}...")
        try:
            if REGION == "us-east-1":
                s3.create_bucket(Bucket=ARTIFACT_BUCKET)
            else:
                s3.create_bucket(
                    Bucket=ARTIFACT_BUCKET,
                    CreateBucketConfiguration={"LocationConstraint": REGION}
                )
            
            # Abilita versioning (raccomandato per CodePipeline)
            s3.put_bucket_versioning(
                Bucket=ARTIFACT_BUCKET,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            print(f"✅ Bucket creato con versioning abilitato")
        except Exception as e:
            print(f"❌ Errore bucket: {e}")


def ensure_codebuild_project(codebuild_role_arn):
    """Crea o aggiorna il progetto CodeBuild."""
    try:
        codebuild.batch_get_projects(names=[CODEBUILD_PROJECT])
        print(f"✅ Progetto CodeBuild {CODEBUILD_PROJECT} esistente")
        
        # Aggiorna il progetto
        codebuild.update_project(
            name=CODEBUILD_PROJECT,
            serviceRole=codebuild_role_arn,
            artifacts={
                'type': 'CODEPIPELINE'
            },
            environment={
                'type': 'LINUX_CONTAINER',
                'image': 'aws/codebuild/standard:7.0',
                'computeType': 'BUILD_GENERAL1_SMALL',
                'privilegedMode': False
            },
            source={
                'type': 'CODEPIPELINE'
            }
        )
        print("✅ Progetto CodeBuild aggiornato")
        
    except:
        print(f"🔨 Creo progetto CodeBuild {CODEBUILD_PROJECT}...")
        try:
            codebuild.create_project(
                name=CODEBUILD_PROJECT,
                source={
                    'type': 'CODEPIPELINE'
                },
                artifacts={
                    'type': 'CODEPIPELINE'
                },
                environment={
                    'type': 'LINUX_CONTAINER',
                    'image': 'aws/codebuild/standard:7.0',
                    'computeType': 'BUILD_GENERAL1_SMALL',
                    'privilegedMode': False
                },
                serviceRole=codebuild_role_arn
            )
            print("✅ Progetto CodeBuild creato")
        except Exception as e:
            print(f"❌ Errore creazione CodeBuild: {e}")


def create_pipeline(pipeline_role_arn):
    """Crea o aggiorna la pipeline CodePipeline."""
    full_repository_id = f"{REPOSITORY_OWNER}/{REPOSITORY_NAME}"
    
    pipeline_structure = {
        "name": PIPELINE_NAME,
        "roleArn": pipeline_role_arn,
        "artifactStore": {
            "type": "S3",
            "location": ARTIFACT_BUCKET
        },
        "stages": [
            {
                "name": "Source",
                "actions": [
                    {
                        "name": "Source",
                        "actionTypeId": {
                            "category": "Source",
                            "owner": "AWS",
                            "provider": "CodeStarSourceConnection",
                            "version": "1"
                        },
                        "configuration": {
                            "ConnectionArn": CODE_CONNECTION_ARN,
                            "FullRepositoryId": full_repository_id,
                            "BranchName": BRANCH,
                            "OutputArtifactFormat": "CODE_ZIP"
                        },
                        "outputArtifacts": [{"name": "SourceOutput"}],
                        "runOrder": 1
                    }
                ]
            },
            {
                "name": "Build",
                "actions": [
                    {
                        "name": "Build",
                        "actionTypeId": {
                            "category": "Build",
                            "owner": "AWS",
                            "provider": "CodeBuild",
                            "version": "1"
                        },
                        "configuration": {
                            "ProjectName": CODEBUILD_PROJECT
                        },
                        "inputArtifacts": [{"name": "SourceOutput"}],
                        "outputArtifacts": [{"name": "BuildOutput"}],
                        "runOrder": 1
                    }
                ]
            }
        ]
    }

    try:
        response = codepipeline.get_pipeline(name=PIPELINE_NAME)
        print(f"🔄 Aggiorno pipeline esistente {PIPELINE_NAME}...")
        
        # Aggiorna la pipeline esistente
        existing_pipeline = response['pipeline']
        existing_pipeline['roleArn'] = pipeline_role_arn
        existing_pipeline['stages'] = pipeline_structure['stages']
        existing_pipeline['artifactStore'] = pipeline_structure['artifactStore']
        
        # Rimuovi metadata non validi
        if 'metadata' in existing_pipeline:
            del existing_pipeline['metadata']
        
        codepipeline.update_pipeline(pipeline=existing_pipeline)
        print("✅ Pipeline aggiornata!")
        
    except codepipeline.exceptions.PipelineNotFoundException:
        print(f"🔨 Creo nuova pipeline {PIPELINE_NAME}...")
        codepipeline.create_pipeline(pipeline=pipeline_structure)
        print("✅ Pipeline creata!")
        
    except Exception as e:
        print(f"❌ Errore pipeline: {e}")


def main():
    print("\n🚀 SETUP COMPLETO AWS CODEPIPELINE\n")
    
    # Step 1: Bucket S3
    print("1️⃣ CONFIGURAZIONE BUCKET S3")
    ensure_bucket()
    
    # Step 2: Ruolo CodeBuild
    print("\n2️⃣ CONFIGURAZIONE RUOLO CODEBUILD")
    codebuild_role_arn = ensure_codebuild_role()
    
    # Step 3: Progetto CodeBuild
    print("\n3️⃣ CONFIGURAZIONE PROGETTO CODEBUILD")
    ensure_codebuild_project(codebuild_role_arn)
    
    # Step 4: Ruolo Pipeline
    print("\n4️⃣ CONFIGURAZIONE RUOLO PIPELINE")
    pipeline_role_arn = ensure_pipeline_role()
    
    # Step 5: Pipeline
    print("\n5️⃣ CONFIGURAZIONE PIPELINE")
    create_pipeline(pipeline_role_arn)
    
    print("\n✅ SETUP COMPLETATO!")
    print(f"\n🔗 Vai su: https://console.aws.amazon.com/codesuite/codepipeline/pipelines/{PIPELINE_NAME}/view?region={REGION}")
    print("\n⚠️ IMPORTANTE:")
    print("1. Verifica che il tuo repository abbia un file 'buildspec.yml' nella root")
    print("2. La connessione GitHub deve essere ATTIVA (verifica su CodeConnections)")
    print("3. Attendi 1-2 minuti prima di eseguire la pipeline per la propagazione IAM")


if __name__ == "__main__":
    main()