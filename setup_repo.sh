#!/bin/bash
# Setup script for alfa-agent repository

echo "==============================================="
echo "  Alpha Agent - Repository Setup"
echo "==============================================="

# Navigate to script directory
cd "$(dirname "$0")"

# Check if git remote exists
if git remote get-url origin &>/dev/null; then
    echo "✓ Remote origin already configured"
else
    echo ""
    echo "Creating GitHub repository..."
    echo ""
    
    # Option 1: Try using gh CLI
    echo "Attempting to create repository with gh CLI..."
    gh repo create alfa-agent --public --description "Alpha - Multi-Agent Reddit Marketing & Distribution System" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✓ Repository created successfully!"
        echo "Adding remote origin..."
        git remote add origin https://github.com/infinityempire/alfa-agent.git
    else
        echo ""
        echo "⚠️  Could not create repository automatically."
        echo ""
        echo "Please create the repository manually:"
        echo "  1. Go to: https://github.com/new"
        echo "  2. Repository name: alfa-agent"
        echo "  3. Select: Public"
        echo "  4. Click 'Create repository'"
        echo ""
        echo "Then run:"
        echo "  git remote add origin https://github.com/infinityempire/alfa-agent.git"
    fi
fi

echo ""
echo "Pushing to remote..."
git branch -M main
git push -u origin main --force 2>&1

echo ""
echo "==============================================="
echo "  Setup Complete!"
echo "==============================================="
echo ""
echo "Repository URL: https://github.com/infinityempire/alfa-agent"
echo ""
