.PHONY: up down status logs clean dev-server dev-classifier dev-desktop

up:
	docker compose up -d
	@echo "Services starting..."
	@sleep 5
	@$(MAKE) status

down:
	docker compose down

status:
	@echo "=== Service Status ==="
	@docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

logs:
	docker compose logs -f --tail=50

clean:
	docker compose down -v
	@echo "Volumes removed."

dev-server:
	cd server && uvicorn main:app --host 0.0.0.0 --port 5056 --reload

dev-classifier:
	cd classifier && uvicorn main:app --host 0.0.0.0 --port 5057 --reload

dev-desktop:
	cd desktop && npm run dev
