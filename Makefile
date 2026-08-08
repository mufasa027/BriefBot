.PHONY: install run ingest test lint docker clean health

install:
	pip install -r requirements.txt

run:
	streamlit run app.py

ingest:
	python main.py

test:
	pytest tests/ -v

lint:
	black .

docker:
	docker build -t cipherbrief:latest .

clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf venv

health:
	python -c "from database.diagnostics import run_database_diagnostics; print(run_database_diagnostics())"
