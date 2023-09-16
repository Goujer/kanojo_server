#!/bin/sh

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
cd $DIR

PY="venv/bin/python"

USERS_PY="$DIR/user_tests.py"
KANOJO_PY="$DIR/kanojo_tests.py"
STORE_PY="$DIR/store_tests.py"
REACTIONWORD_PY="$DIR/reactionword_tests.py"

#$PY $USERS_PY && $PY $KANOJO_PY && $PY $STORE_PY && $PY $REACTIONWORD_PY

$PY user_tests.py && $PY kanojo_tests.py && $PY store_tests.py && $PY reactionword_tests.py && $PY activity_tests.py

exit $?
