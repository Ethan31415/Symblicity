#!/bin/sh
set -eu
PREFIX=${PREFIX:-"$HOME/.local"}
rm -f "$PREFIX/bin/sym"
printf 'Removed %s/bin/sym\n' "$PREFIX"
