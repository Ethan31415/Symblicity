# Terminal Zero groundwork

This is the first Symblicity-native shell for **Terminal Zero**.

## Current main menu

- Enters the ANSI alternate screen and hides the cursor.
- Draws the TERMINAL ZERO title.
- Uses sparse animated binary rain made only from `0` and `1`.
- Menu entries are `START`, `CONTINUE`, and `EXIT`.
- Only the selected word receives reverse-video highlighting; surrounding whitespace is never highlighted.
- `W/S` move the selection.
- `E` or Enter activates it.
- The menu expects a finite input wait (80 ms recommended) so animation continues while idle.
- START currently opens a core-initialization scene and returns to the menu after one key.
- CONTINUE is a placeholder until save-state serialization is connected.
- EXIT restores normal attributes, shows the cursor, and leaves the alternate screen.

Run it with:

```sh
sym -u --input-wait 80 examples/terminal_zero.sym
```

## Runtime memory groundwork

```text
0x0200  menu selection
0x0201  last input byte
0x0202  exit flag
0x0203  animation frame counter
0x0204  animation seed (initialized from 0xFEFF system-time byte)
0x0205  animation row
0x0206  animation column
0x0207  animation glyph
0x0208  temporary byte
0x0209  last audio event

0x0300  entity 0 type
0x0301  entity 0 x
0x0302  entity 0 y
0x0303  entity 0 width
0x0304  entity 0 height
0x0305  entity 0 animation frame
0x0306  entity 0 flags
0x0310  pending movement direction
```

The first entity is initialized as a 3x3 player-sized entity. This is deliberately
larger than a traditional one-character roguelike actor.

## Subroutine map

```text
a  setup / title / initial menu
b  redraw menu selection
c  binary-rain animation tick
d  input dispatcher
f  draw one animated binary cell
h  selection up
i  selection down
j  activate menu selection
k  START placeholder scene
l  CONTINUE placeholder
n  request exit
o  terminal cleanup
p  entity initialization
q  entity movement core
r  audio-state initialization
s  animation initialization / time seed
```

All of these use the nested parenthesis return stack, so later game routines can
call animation, entity, movement, rendering, and audio helpers recursively/nested
without reverting to the old single-return convention.

## Entity direction convention

The initial movement core uses `0x0310`:

```text
0 = up
1 = down
2 = left
3 = right
```

It updates the anchor at `0x0301/0x0302`. Width and height are already part of
the record so collision/rendering can treat future ASCII sprites as multi-cell entities.

## Next engine layer

The next useful step is to replace the START placeholder with the room renderer,
sprite-table format, collision rectangles, and a proper entity list while keeping
this menu/animation shell unchanged.
