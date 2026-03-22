#!/bin/bash -eEu

set -eEux
set -o pipefail

MODULES_CHANGED=""
GITHUB_STEP_SUMMARY=${GITHUB_STEP_SUMMARY:-/proc/self/fd/1}

# Only check the rr submodule for updates
SUBMODULE_NAME="rr"
SUBMODULE_SHA="$(git submodule status $SUBMODULE_NAME | awk '{print $1}')"
# The submodule may not be initialized so there'll be a '-' or '+' prefix
SUBMODULE_SHA="${SUBMODULE_SHA#[-+]}"

SUBMODULE_URL="$(git config -f .gitmodules submodule.$SUBMODULE_NAME.url)"
SUBMODULE_BRANCH="$(git config -f .gitmodules submodule.$SUBMODULE_NAME.branch)"
read -r REMOTE_SHA REMOTE_REF <<<"$(git ls-remote $SUBMODULE_URL | grep 'refs/heads/'$SUBMODULE_BRANCH)"

if [ "$SUBMODULE_SHA" != "$REMOTE_SHA" ]; then
    echo "## Submodule $SUBMODULE_NAME @ $SUBMODULE_URL/tree/$SUBMODULE_BRANCH local $SUBMODULE_SHA vs remote $REMOTE_SHA" >> $GITHUB_STEP_SUMMARY
    MODULES_CHANGED="1"
else
    echo "## Submodule $SUBMODULE_NAME @ $SUBMODULE_URL/tree/$SUBMODULE_BRANCH local $SUBMODULE_SHA unchanged" >> $GITHUB_STEP_SUMMARY
fi

# Check if the remote HEAD has a new tag we haven't seen
read -r REMOTE_TAG_SHA REMOTE_TAG <<<"$(git ls-remote --tags $SUBMODULE_URL | (grep $REMOTE_SHA || true) | sed -e 's/[\^\{\}]//g' | sed -e 's|refs/tags/||')"
if [ -n "${REMOTE_TAG:-}" ]; then
    echo "## Remote tag $REMOTE_TAG is present" >> $GITHUB_STEP_SUMMARY
    REMOTE_TAG_LOCALLY_PRESENT="$(git show-ref --tags | (grep $REMOTE_TAG || true))"
    if [ -z "$REMOTE_TAG_LOCALLY_PRESENT" ]; then
        echo "## Remote tag $REMOTE_TAG is not present locally!" >> $GITHUB_STEP_SUMMARY
        MODULES_CHANGED="1"
    fi
fi
