param (
    [string]$Command = "dev"
)

switch ($Command) {
    "dev" {
        Write-Host "Starting Development Server..."
        docker-compose down
        docker-compose up --build
    }
    "ingest" {
        Write-Host "Running Ingest Command..."
        # This fixes your 'service not found' error by ensuring we use the correct service name
        docker-compose exec web python manage.py ingest_dmarc
    }
    "reset" {
        Write-Host "Wiping Database and Resetting..."
        docker-compose down -v
        docker-compose up --build
    }
    Default {
        Write-Host "Usage: .\manage.ps1 [dev|ingest|reset]"
    }
}