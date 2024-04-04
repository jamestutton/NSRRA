#!/bin/bash

if [ -f venv/bin/activate ]; then
    . venv/bin/activate
    poetry --version
else
    # set up venv
    python3 -m venv venv
    . venv/bin/activate
    pip install --upgrade pip
    # Install poetry
    pip install poetry
    poetry --version
    poetry config virtualenvs.in-project true
    poetry install -vv
fi
pip install -r requirements.txt
python3 ./NSRRA_Parser.py