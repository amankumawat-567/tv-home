# Starter wallpaper pack

Eight real photos, originally from Unsplash and fetched via [Lorem
Picsum](https://picsum.photos) (a free Unsplash mirror — no API key needed),
each given the same dark gradient tint so a random pick always matches TV
Home's "dark, calm" look (`docs/DESIGN.md`) instead of clashing with it. See
`CREDITS.md` for per-photo attribution.

License: Unsplash photos are free to use under the
[Unsplash License](https://unsplash.com/license) (no permission or
attribution required, though it's given above anyway).

## Regenerating / adding more

```sh
pip install pillow
python3 scripts/fetch-wallpapers.py
```

Edit the `CURATED` dict in `scripts/fetch-wallpapers.py` to change the set —
it maps a Picsum photo id to an output name. To find new ones, browse
`https://picsum.photos/v2/list?page=N&limit=30` and preview a candidate at
`https://picsum.photos/id/<id>/480/270` before committing to it.

## How these get onto the TV

`session/install.sh` copies this folder to `~/.config/tv-home/wallpapers/`,
which is the first place `backend/tv_home/wallpaper.py` looks (ahead of any
system backdrops). Settings → Wallpaper cycles through whatever's there.
