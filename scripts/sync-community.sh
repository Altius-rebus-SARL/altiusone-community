#!/bin/bash
# sync-community.sh
# Propage les commits metier de main vers community et pousse sur le repo public.
#
# Usage:
#   ./scripts/sync-community.sh <commit-hash>           # Cherry-pick un commit
#   ./scripts/sync-community.sh <hash1> <hash2> ...     # Cherry-pick plusieurs commits
#   ./scripts/sync-community.sh --push                  # Push community vers le repo public
#   ./scripts/sync-community.sh <commit-hash> --push    # Cherry-pick + push

set -e

CURRENT_BRANCH=$(git branch --show-current)
PUSH=false
COMMITS=()

# Parser les arguments
for arg in "$@"; do
    if [ "$arg" = "--push" ]; then
        PUSH=true
    else
        COMMITS+=("$arg")
    fi
done

# Cherry-pick des commits si fournis
if [ ${#COMMITS[@]} -gt 0 ]; then
    echo "==> Basculement sur community..."
    git checkout community

    for commit in "${COMMITS[@]}"; do
        echo "==> Cherry-pick $commit..."
        git cherry-pick "$commit"
    done

    echo "==> Retour sur $CURRENT_BRANCH..."
    git checkout "$CURRENT_BRANCH"
fi

# Push vers le repo public si demande
if [ "$PUSH" = true ]; then
    echo "==> Push community vers le repo public (altiusone-community)..."
    git push community community:main
    echo "==> Push community vers origin..."
    git push origin community
    echo "==> Done. Repo public mis a jour."
else
    if [ ${#COMMITS[@]} -gt 0 ]; then
        echo ""
        echo "Commits propages vers community. Pour pousser vers le repo public :"
        echo "  ./scripts/sync-community.sh --push"
    fi
fi
