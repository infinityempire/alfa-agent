#!/bin/bash
# Setup script for alfa-agent repository

set -e

echo "==============================================="
echo "  Alpha Agent - Repository Setup"
echo "==============================================="

# Navigate to script directory
cd "$(dirname "$0")"

# Check if git remote exists
if git remote get-url origin &>/dev/null; then
    echo "Remote already configured"
else
    echo ""
    echo "Creating GitHub repository..."
    
    # Try gh CLI first
    if gh repo create alfa-agent --public --description "Alpha - Multi-Agent Reddit Marketing & Distribution System" 2>/dev/null; then
        echo "Repository created with gh CLI"
        git remote add origin https://github.com/infinityempire/alfa-agent.git
    else
        echo ""
        echo "Could not create repository automatically."
        echo ""
        echo "Please create manually:"
        echo "  1. Go to: https://github.com/new"
        echo "  2. Name: alfa-agent"
        echo "  3. Select: Public"
        echo "  4. Click: Create repository"
        echo ""
        echo "Then run:"
        echo "  git remote add origin https://github.com/infinityempire/alfa-agent.git"
        echo "  ./setup_repo.sh"
        exit 1
    fi
fi

echo ""
echo "Pushing to remote..."
git branch -M main
git push -u origin main

echo ""
echo "==============================================="
echo "  Setup Complete!"
echo "Repository: https://github.com/infinityempire/alfa-agent"
echo "==============================================="
