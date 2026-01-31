#!/bin/bash
echo "Pushing amb_w_tds to GitHub..."
git add .
git commit -m "Update: $(date '+%Y-%m-%d %H:%M:%S')" 2>/dev/null || echo "No changes"
git push origin $(git branch --show-current)
echo "✓ Done!"
