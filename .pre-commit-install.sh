#!/bin/bash
# ABOUTME: Script to install pre-commit hooks in the repository
# ABOUTME: Run this once after cloning to enable automatic code quality checks

set -e

echo "Installing pre-commit hooks..."

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "pre-commit not found. Installing..."
    pip install pre-commit
fi

# Install the hooks
pre-commit install

echo "✓ Pre-commit hooks installed successfully!"
echo "Hooks will now run automatically before each commit."
echo ""
echo "To run hooks manually on all files:"
echo "  pre-commit run --all-files"
