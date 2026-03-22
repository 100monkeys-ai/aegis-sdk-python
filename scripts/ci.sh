#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026 100monkeys.ai

set -e

# Change directory to the repository root
cd "$(dirname "$0")/.."

# Check if a virtual environment exists; if not, create one.
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate the virtual environment
source .venv/bin/activate

# Install dependencies including dev dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install ".[dev]"

# Run formatting check
echo "Running formatting check (black)..."
black --check aegis

# Run linting (ruff)
echo "Running linting (ruff)..."
ruff check aegis

# Run type checking (mypy)
echo "Running type checking (mypy)..."
mypy aegis

# Run tests
if [ -d "tests" ]; then
    echo "Running tests..."
    pytest
else
    echo "No tests found. Skipping."
fi

# Build verification
echo "Building package..."
python3 -m pip install build
python3 -m build

echo "CI pipeline completed successfully."
