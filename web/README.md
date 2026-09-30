# Symblicity browser playground

`site.tar.gz` contains the complete static browser playground deployed to GitHub Pages.
It contains plain HTML, CSS and JavaScript plus the current Battleship `.sym` example.

The Pages workflow extracts it without a build tool:

```sh
mkdir -p _site
tar -xzf web/site.tar.gz -C _site
```

To inspect the browser source locally:

```sh
mkdir web-site
cd web-site
tar -xzf ../web/site.tar.gz
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

The browser implementation uses Web Audio, so it has no FFmpeg/ffplay dependency.
Built-in Battleship sounds are synthesized at runtime.
