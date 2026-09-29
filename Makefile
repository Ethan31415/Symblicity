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
	@echo "Symblicity smoke test passed"

install: $(BIN)
	install -d "$(DESTDIR)$(PREFIX)/bin"
	install -m 755 $(BIN) "$(DESTDIR)$(PREFIX)/bin/sym"

uninstall:
	rm -f "$(DESTDIR)$(PREFIX)/bin/sym"

clean:
	rm -rf bin
