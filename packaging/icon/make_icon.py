"""Draw the Research Suite icon and write it in every format the build needs.

Design: a flat indigo rounded square (the International Tax Network Lab's accent colour), in the flat
style of the A-share Company Intelligence icon. Three nodes joined in a triangle stand for the three
tools and their levels of analysis: red for firms (A-share Company Intelligence), green for networks
(the Lab) and amber for regimes (JAF Rule Bench). A white hub at the centre, linked to each, stands
for the shared core. At 16 to 48 pixels the hub is left out so the three nodes stay legible.

Run from the repository root (needs Pillow, a development-only dependency):

    python packaging/icon/make_icon.py

Outputs (committed, so a build does not need Pillow):
    packaging/icon/research_suite.svg       editable source of the design
    packaging/research_suite.ico            Windows icon, 16 to 256 px
    src/rscore/launcher/assets/icon_48.png  window header image
    src/rscore/launcher/assets/icon_64.png  window header image (large text settings)
    src/rscore/launcher/assets/icon_256.png window icon on other systems
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SIZE = 1024  # design grid; everything below is in these units
SUPERSAMPLE = 4

BACKGROUND = "#4338CA"
WHITE = "#FFFFFF"
FIRM, NETWORK, REGIME = "#EF4444", "#10B981", "#F59E0B"

CORNER = 220
NODES = {"firm": ((512, 298), FIRM), "network": ((272, 726), NETWORK), "regime": ((752, 726), REGIME)}
HUB = (512, 584)
EDGE_WIDTH, SPOKE_WIDTH = 40, 26
NODE_RADIUS, RING, HUB_RADIUS = 118, 30, 54

# Sizes up to 48 px: no hub, heavier edges, larger nodes.
SMALL = {"edge": 78, "node": 170, "ring": 44}


def _draw(px: int, small: bool) -> Image.Image:
    s = px * SUPERSAMPLE / SIZE
    img = Image.new("RGBA", (px * SUPERSAMPLE,) * 2, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, SIZE * s - 1, SIZE * s - 1], radius=CORNER * s, fill=BACKGROUND)
    pts = [p for p, _ in NODES.values()]
    edge = (SMALL["edge"] if small else EDGE_WIDTH) * s
    for a, b in ((0, 1), (1, 2), (2, 0)):
        d.line([tuple(v * s for v in pts[a]), tuple(v * s for v in pts[b])], fill=WHITE, width=round(edge))
    if not small:
        for p in pts:
            d.line([tuple(v * s for v in HUB), tuple(v * s for v in p)], fill=WHITE, width=round(SPOKE_WIDTH * s))
        r = HUB_RADIUS * s
        d.ellipse([HUB[0] * s - r, HUB[1] * s - r, HUB[0] * s + r, HUB[1] * s + r], fill=WHITE)
    node, ring = (SMALL["node"], SMALL["ring"]) if small else (NODE_RADIUS, RING)
    for (x, y), colour in NODES.values():
        r = node * s
        d.ellipse([x * s - r, y * s - r, x * s + r, y * s + r], fill=WHITE)
        r = (node - ring) * s
        d.ellipse([x * s - r, y * s - r, x * s + r, y * s + r], fill=colour)
    return img.resize((px, px), Image.LANCZOS)


def icon(px: int) -> Image.Image:
    return _draw(px, small=px <= 48)


def svg() -> str:
    pts = [p for p, _ in NODES.values()]
    edges = "".join(
        f'<line x1="{pts[a][0]}" y1="{pts[a][1]}" x2="{pts[b][0]}" y2="{pts[b][1]}"/>' for a, b in ((0, 1), (1, 2), (2, 0)))
    spokes = "".join(f'<line x1="{HUB[0]}" y1="{HUB[1]}" x2="{x}" y2="{y}"/>' for x, y in pts)
    nodes = "".join(
        f'<circle cx="{x}" cy="{y}" r="{NODE_RADIUS}" fill="{WHITE}"/>'
        f'<circle cx="{x}" cy="{y}" r="{NODE_RADIUS - RING}" fill="{c}"/>' for (x, y), c in NODES.values())
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}" role="img" aria-label="Research Suite">\n'
        f'  <rect width="{SIZE}" height="{SIZE}" rx="{CORNER}" fill="{BACKGROUND}"/>\n'
        f'  <g stroke="{WHITE}" stroke-linecap="round" stroke-width="{EDGE_WIDTH}">{edges}</g>\n'
        f'  <g stroke="{WHITE}" stroke-linecap="round" stroke-width="{SPOKE_WIDTH}">{spokes}</g>\n'
        f'  <circle cx="{HUB[0]}" cy="{HUB[1]}" r="{HUB_RADIUS}" fill="{WHITE}"/>\n'
        f'  {nodes}\n'
        f'</svg>\n'
    )


def main() -> None:
    (ROOT / "packaging/icon/research_suite.svg").write_text(svg(), encoding="utf-8")
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    frames = [icon(px) for px in sizes]
    frames[-1].save(ROOT / "packaging/research_suite.ico", sizes=[(px, px) for px in sizes],
                    append_images=frames[:-1])
    assets = ROOT / "src/rscore/launcher/assets"
    assets.mkdir(parents=True, exist_ok=True)
    icon(48).save(assets / "icon_48.png")
    icon(64).save(assets / "icon_64.png")
    icon(256).save(assets / "icon_256.png")


if __name__ == "__main__":
    main()
