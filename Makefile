CC ?= cc
CFLAGS ?= -O2 -std=c11 -Wall -Wextra -Wpedantic
PREFIX ?= /usr/local
DESTDIR ?=
BIN := bin/sym
SRC := src/symblicity.c

.PHONY: all clean install uninstall test

all: $(BIN)

$(BIN): $(SRC)
	@mkdir -p bin
	$(CC) $(CFLAGS) $(SRC) -o $(BIN)

test: $(BIN)
	@test "$$($(BIN) examples/hello.sym)" = "HelloWorld!"
	@tmp=$$(mktemp); trap 'rm -f "$$tmp"' EXIT; \
		printf "%s" "0'?8," > "$$tmp"; \
		test "$$(printf "" | $(BIN) --input-wait 0 "$$tmp")" = "1"; \
		test "$$(printf "A" | $(BIN) --input-wait 50 "$$tmp")" = "64"; \
		test "$$(printf "A" | $(BIN) "$$tmp")" = "65"; \
		printf "%s" "0.?8," > "$$tmp"; \
		test "$$(printf "42\n" | $(BIN) --input-wait 50 "$$tmp")" = "41"; \
		test "$$(printf "42\n" | $(BIN) "$$tmp")" = "42"
	@rm -f .sym_file_test.bin; trap 'rm -f .sym_file_test.bin' EXIT; \
		$(BIN) tests/file_write.sym; \
		test "$$(cat .sym_file_test.bin)" = "ABC"; \
		test "$$($(BIN) tests/file_read.sym)" = "ABC1"
	@a=$$($(BIN) tests/time_byte.sym); sleep 0.02; b=$$($(BIN) tests/time_byte.sym); \
		test "$$a" != "$$b"
	@printf "ssse" | $(BIN) --input-wait 0 examples/terminal_zero.sym >/dev/null
	@python3 -c 'from pathlib import Path; s=Path("examples/terminal_zero.sym").read_text(); style="`0134\"6\"5679\"9\"2\"8999\"9\"6899\""; assert len(style)==29; assert s.count("`589?#"+style)==4, "Terminal Zero menu highlight skip length drifted"; assert "`4210?#"+style not in s, "stale 23-character menu highlight skip remains"'
	@echo "Symblicity smoke/input/file/time/Terminal Zero tests passed"

install: $(BIN)
	install -d "$(DESTDIR)$(PREFIX)/bin"
	install -m 755 $(BIN) "$(DESTDIR)$(PREFIX)/bin/sym"

uninstall:
	rm -f "$(DESTDIR)$(PREFIX)/bin/sym"

clean:
	rm -rf bin
