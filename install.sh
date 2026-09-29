#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PREFIX=${PREFIX:-"$HOME/.local"}
CC=${CC:-cc}
CFLAGS=${CFLAGS:-"-O2 -std=c11 -Wall -Wextra -Wpedantic"}
mkdir -p "$PREFIX/bin"
# shellcheck disable=SC2086
$CC $CFLAGS "$ROOT/src/symblicity.c" -o "$PREFIX/bin/sym"
printf 'Installed Symblicity: %s\n' "$PREFIX/bin/sym"
case ":$PATH:" in
  *":$PREFIX/bin:"*) ;;
  *) printf 'Add %s/bin to PATH to run: sym program.sym\n' "$PREFIX" ;;
esac
