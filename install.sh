#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PREFIX=${PREFIX:-"$HOME/.local"}
CC=${CC:-cc}
CFLAGS=${CFLAGS:-"-O2 -std=c11 -Wall -Wextra -Wpedantic"}

run_root() {
	if [ "$(id -u)" -eq 0 ]; then
		"$@"
	elif command -v sudo >/dev/null 2>&1; then
		sudo "$@"
	else
		printf '%s\n' "Administrator privileges are required, but sudo was not found." >&2
		return 1
	fi
}

install_ffplay() {
	if command -v ffplay >/dev/null 2>&1; then
		printf '%s\n' "ffplay is already installed."
		return 0
	fi

	printf '\nffplay was not found.\n'
	printf 'Symblicity audio uses ffplay from FFmpeg.\n'
	printf 'Install FFmpeg/ffplay now? [y/N] '
	if ! IFS= read -r answer; then
		answer=
	fi

	case "$answer" in
		y|Y|yes|YES|Yes)
			printf '%s\n' "Installing FFmpeg. Your package manager may request administrator permission."
			;;
		*)
			printf '%s\n' "Skipping FFmpeg/ffplay installation."
			return 0
			;;
	esac

	if command -v apt-get >/dev/null 2>&1; then
		# Do not run apt-get update here: unrelated broken third-party repositories
		# can make update fail even when the cached Ubuntu/Debian package index
		# already contains FFmpeg.
		if ! run_root apt-get install -y ffmpeg; then
			printf '%s\n' "Could not install FFmpeg with the current APT package index." >&2
			printf '%s\n' "If APT reports a broken repository, repair/disable that repository and retry." >&2
			return 0
		fi
	elif command -v dnf >/dev/null 2>&1; then
		if ! run_root dnf install -y ffmpeg-free; then
			run_root dnf install -y ffmpeg
		fi
	elif command -v yum >/dev/null 2>&1; then
		run_root yum install -y ffmpeg
	elif command -v pacman >/dev/null 2>&1; then
		run_root pacman -S --needed --noconfirm ffmpeg
	elif command -v zypper >/dev/null 2>&1; then
		run_root zypper --non-interactive install ffmpeg
	elif command -v apk >/dev/null 2>&1; then
		run_root apk add ffmpeg
	elif command -v brew >/dev/null 2>&1; then
		brew install ffmpeg
	elif command -v pkg >/dev/null 2>&1; then
		run_root pkg install -y ffmpeg
	else
		printf '%s\n' "No supported package manager was found." >&2
		printf '%s\n' "Install FFmpeg manually if you want Symblicity audio." >&2
		return 0
	fi

	if command -v ffplay >/dev/null 2>&1; then
		printf 'Installed ffplay: %s\n' "$(command -v ffplay)"
	else
		printf '%s\n' "FFmpeg installation completed, but ffplay is still not available in PATH." >&2
		printf '%s\n' "Symblicity itself is installed and can still run without audio." >&2
	fi
}

mkdir -p "$PREFIX/bin"

# shellcheck disable=SC2086
$CC $CFLAGS "$ROOT/src/symblicity.c" -o "$PREFIX/bin/sym"

printf 'Installed Symblicity: %s\n' "$PREFIX/bin/sym"

case ":$PATH:" in
	*":$PREFIX/bin:"*) ;;
	*) printf 'Add %s/bin to PATH to run: sym program.sym\n' "$PREFIX" ;;
esac

install_ffplay
