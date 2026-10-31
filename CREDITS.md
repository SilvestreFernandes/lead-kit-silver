# Credits and attribution

This page lists who built what in the Google Maps Scraper Kit, and the license that covers the engine.

The kit is designed and built by Mahan ([@Mahanaicoach](https://github.com/Mahanaicoach)).
One component, the Google Maps scraping engine, is open-source work by Georgios Komninos, credited below.

## Scraping engine

- **Project:** google-maps-scraper
- **Author:** **Georgios Komninos** ([@gosom](https://github.com/gosom))
- **Repository:** https://github.com/gosom/google-maps-scraper
- **License:** MIT License, Copyright (c) 2023 Georgios Komninos
- **Docker image used:** `gosom/google-maps-scraper`

The kit runs the engine's official Docker image, unmodified. Everything else in this repository is
original to the kit: local deployment, lead-field cleaning, CSV output, auto-geocoding, batch jobs,
social profile enrichment, and the Claude Code skill and slash commands.

## Engine license (reproduced as required by MIT)

```
MIT License

Copyright (c) 2023 Georgios Komninos

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

To support the engine's author, star the repository: https://github.com/gosom/google-maps-scraper

## Location service (city to coordinates)

- **Service:** Nominatim, run by the OpenStreetMap Foundation (https://nominatim.openstreetmap.org)
- **Data:** (c) OpenStreetMap contributors, available under the Open Database License (ODbL): https://www.openstreetmap.org/copyright
- **Use in the kit:** only the city name, the state and the country are sent, to find the coordinates of the search area. Results are cached on disk, with at most one request per second and a User-Agent that identifies the kit, as the usage policy asks: https://operations.osmfoundation.org/policies/nominatim/

## Fonts used in the design prototypes (docs/design)

These fonts are only in the static design prototypes in `docs/design/`, not in the panel. If a visual direction is chosen, the matching fonts move into `kit/painel/` and stay listed here. All files are served from the kit itself, never from a font service.

- **IBM Plex Sans** and **IBM Plex Mono**: Copyright 2017 and 2019 IBM Corp. SIL Open Font License 1.1. https://github.com/IBM/plex . License text: `docs/design/fontes/LICENCA-IBM-Plex.txt`
- **Atkinson Hyperlegible Next**: Copyright 2020-2024 The Atkinson Hyperlegible Next Project Authors. SIL Open Font License 1.1. https://github.com/googlefonts/atkinson-hyperlegible-next . License text: `docs/design/fontes/LICENCA-Atkinson-Hyperlegible-Next.txt`

The font files come from the `@fontsource` npm packages (latin subset, woff2), which republish the original fonts under the same license.

## Development tools (not part of the product)

- **Impeccable** (Apache 2.0, https://github.com/pbakaus/impeccable) is used only on the developer machine to review the design. Its files live in `.claude/` and are kept out of git and out of the product package.
