import boto3

# Configurazione
CODECOMMIT_REPO = "gymcloud-repo"
REGION = "us-east-1"

# Client AWS
codecommit = boto3.client("codecommit", region_name=REGION)

def ensure_codecommit_repo():
    """Crea il repository CodeCommit se non esiste."""
    try:
        codecommit.get_repository(repositoryName=CODECOMMIT_REPO)
        print(f"✅ Repository {CODECOMMIT_REPO} già esistente.")
    except codecommit.exceptions.RepositoryDoesNotExistException:
        print(f"🔨 Creazione repository {CODECOMMIT_REPO}...")
        codecommit.create_repository(
            repositoryName=CODECOMMIT_REPO,
            repositoryDescription="Repository per il frontend GymCloud"
        )
        print(f"✅ Repository {CODECOMMIT_REPO} creato con successo!")
    except Exception as e:
        # Questo cattura l'errore di permessi se il tuo utente/ruolo non ha l'autorizzazione.
        print(f"❌ Errore durante l'accesso/creazione del repository: {e}")
        print("➡️ Assicurati che il tuo utente IAM abbia la policy 'AWSCodeCommitFullAccess'.")

if __name__ == "__main__":
    ensure_codecommit_repo()