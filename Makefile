VENV := .venv
PY := $(VENV)/bin/python

.PHONY: setup run clean dist

setup:
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt

run:
	$(PY) main.py $(ARGS)

clean:
	rm -rf $(VENV) __pycache__ dist build *.build *.dist *.onefile-build main.build

dist:
	$(PY) -m nuitka --mode=standalone --output-dir=dist --assume-yes-for-downloads main.py
