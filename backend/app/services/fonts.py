"""Caption fonts bundled with the renderer (SIL Open Font License, see assets/fonts/*-OFL.txt).

Each entry is a single static face, as served by Google Fonts. Captions only ever use that one
weight, and libass finds it through the render's fontsdir rather than the system font list.
"""

from dataclasses import dataclass
from pathlib import Path

FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"


@dataclass(frozen=True)
class CaptionFont:
    id: str
    label: str
    family: str  # the name libass matches (name table id 1)
    file: str
    bold: bool  # ASS Bold flag; must match the face's weight or libass fakes it

    @property
    def path(self) -> Path:
        return FONT_DIR / self.file


FONTS: dict[str, CaptionFont] = {
    font.id: font
    for font in [
        CaptionFont("montserrat", "Montserrat", "Montserrat ExtraBold", "Montserrat-ExtraBold.ttf",
                    bold=False),
        CaptionFont("inter", "Inter", "Inter", "Inter-Bold.ttf", bold=True),
        CaptionFont("bebas-neue", "Bebas Neue", "Bebas Neue", "BebasNeue-Regular.ttf", bold=False),
        CaptionFont("cinzel", "Cinzel", "Cinzel", "Cinzel-Bold.ttf", bold=True),
        CaptionFont("playfair", "Playfair Display", "Playfair Display", "PlayfairDisplay-Bold.ttf",
                    bold=True),
    ]
}
