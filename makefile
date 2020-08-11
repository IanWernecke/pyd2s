all: build install run;

backup:
	poetry run python -m pyd2s.backup ALL

build:
	poetry build

install:
	poetry install

restore:
	poetry run python -m pyd2s.restore

run:
	poetry run python -m pyd2s

test:
	poetry run pytest tests

