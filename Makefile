# Default: Build and Run
dev:
	docker-compose down
	docker-compose up --build

# Run the Ingress Command manually if needed
ingest:
	docker-compose exec web python manage.py ingest_dmarc

# Wipe the Database and start fresh (Nuclear option)
reset:
	docker-compose down -v
	docker-compose up --build