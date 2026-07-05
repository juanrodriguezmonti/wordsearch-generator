#!/usr/bin/env python3
"""
Amelie, wordsworld — Generador de sopas de letras en español (PDF A4 listo para imprimir).

Uso:
    python wordsworld.py
    python wordsworld.py --nivel facil -o sopa-facil.pdf
    python wordsworld.py --nivel dificil --semilla 42
    python wordsworld.py --descargar-diccionario

Dependencias:
    pip install reportlab
"""

from __future__ import annotations

import argparse
import random
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfgen import canvas
except ImportError:
    print("Falta reportlab. Instalá con: pip install reportlab", file=sys.stderr)
    sys.exit(1)

# Configuración

SCRIPT_DIR = Path(__file__).resolve().parent
CACHE_DIR = SCRIPT_DIR / ".wordsworld"
DEFAULT_DICT_PATH = CACHE_DIR / "es_palabras.txt"

DICT_URLS = (
    "https://raw.githubusercontent.com/studentenherz/spanish-wordlist/master/es_all_with_tilde.txt",
    "https://raw.githubusercontent.com/xavier-hernandez/spanish-wordlist/main/words.txt",
)

SPANISH_LETTERS = "ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"
SPANISH_LETTERS_WEIGHTED = list(SPANISH_LETTERS) + ["A", "E", "O", "I", "U", "S", "R", "N", "L"]

# Direcciones: (dr, dc) — fila, columna
ALL_DIRECTIONS: tuple[tuple[int, int], ...] = (
    (0, 1),    # horizontal →
    (0, -1),   # horizontal ←
    (1, 0),    # vertical ↓
    (-1, 0),   # vertical ↑
    (1, 1),    # diagonal ↘
    (1, -1),   # diagonal ↙
    (-1, 1),   # diagonal ↗
    (-1, -1),  # diagonal ↖
)

HV_DIRECTIONS: tuple[tuple[int, int], ...] = ((0, 1), (0, -1), (1, 0), (-1, 0))
HV_DIAG_DIRECTIONS: tuple[tuple[int, int], ...] = HV_DIRECTIONS + ((1, 1), (1, -1), (-1, 1), (-1, -1))

WORD_RE = re.compile(r"^[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+$")

FALLBACK_WORDS: tuple[str, ...] = (
    "CASA", "MESA", "SOL", "LUNA", "AGUA", "FUEGO", "TIERRA", "CIELO",
    "ARBOL", "FLOR", "PAJARO", "GATO", "PERRO", "LIBRO", "ESCUELA",
    "AMIGO", "FAMILIA", "MUSICA", "DANZA", "PINTURA", "CAMINO", "MONTAÑA",
    "RIO", "MAR", "PLAYA", "BOSQUE", "CIUDAD", "PUEBLO", "CAMPO", "JARDIN",
    "COMIDA", "PAN", "FRUTA", "VERDURA", "CAFE", "LECHE", "HUEVO", "QUESO",
    "COCHE", "TREN", "AVION", "BARCO", "BICICLETA", "CALLE", "PLAZA",
    "DOCTOR", "ENFERMERA", "HOSPITAL", "MEDICINA", "SALUD", "DEPORTE",
    "FUTBOL", "TENIS", "NATACION", "CORRER", "CAMINAR", "JUGAR", "REIR",
    "AMOR", "PAZ", "ALEGRIA", "SUERTE", "TRABAJO", "ESTUDIO", "APRENDER",
    "ESPAÑA", "MEXICO", "ARGENTINA", "CHILE", "COLOMBIA", "PERU", "URUGUAY",
)


@dataclass(frozen=True)
class NivelConfig:
    nombre: str
    titulo: str
    grid_size: int
    word_count: int
    min_len: int
    max_len: int
    directions: tuple[tuple[int, int], ...]
    max_attempts: int = 800


NIVELES: dict[str, NivelConfig] = {
    "facil": NivelConfig(
        nombre="facil",
        titulo="Fácil",
        grid_size=12,
        word_count=10,
        min_len=4,
        max_len=8,
        directions=HV_DIRECTIONS,
    ),
    "medio": NivelConfig(
        nombre="medio",
        titulo="Medio",
        grid_size=15,
        word_count=15,
        min_len=4,
        max_len=10,
        directions=HV_DIAG_DIRECTIONS,
    ),
    "dificil": NivelConfig(
        nombre="dificil",
        titulo="Difícil",
        grid_size=18,
        word_count=20,
        min_len=5,
        max_len=12,
        directions=ALL_DIRECTIONS,
    ),
}


@dataclass
class Placement:
    word: str
    row: int
    col: int
    dr: int
    dc: int


@dataclass
class Puzzle:
    nivel: NivelConfig
    grid: list[list[str]]
    placements: list[Placement] = field(default_factory=list)
    words: list[str] = field(default_factory=list)


# Diccionario


def normalize_word(word: str) -> str:
    return word.strip().upper()


def is_valid_word(word: str, min_len: int, max_len: int) -> bool:
    if not min_len <= len(word) <= max_len:
        return False
    return bool(WORD_RE.match(word))


def download_dictionary(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for url in DICT_URLS:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "wordsworld/1.0 (sopa de letras educativa)"},
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                raw = response.read().decode("utf-8", errors="replace")
            lines = [normalize_word(line) for line in raw.splitlines() if line.strip()]
            unique = sorted(set(lines))
            dest.write_text("\n".join(unique) + "\n", encoding="utf-8")
            print(f"Diccionario descargado: {len(unique):,} palabras → {dest}")
            return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = exc
            print(f"No se pudo descargar desde {url}: {exc}", file=sys.stderr)
    raise RuntimeError(f"No se pudo obtener el diccionario. Último error: {last_error}")


def load_dictionary(path: Path, auto_download: bool = True) -> list[str]:
    if not path.exists():
        if auto_download:
            print(f"Descargando diccionario en {path}…")
            download_dictionary(path)
        else:
            print("Usando lista de respaldo integrada.", file=sys.stderr)
            return list(FALLBACK_WORDS)
    text = path.read_text(encoding="utf-8", errors="replace")
    return [normalize_word(w) for w in text.splitlines() if w.strip()]


def pick_words(pool: Iterable[str], config: NivelConfig, rng: random.Random) -> list[str]:
    candidates = [w for w in pool if is_valid_word(w, config.min_len, config.max_len)]
    if len(candidates) < config.word_count:
        extra = [w for w in FALLBACK_WORDS if is_valid_word(w, config.min_len, config.max_len)]
        candidates = list(set(candidates) | set(extra))
    if len(candidates) < config.word_count:
        raise RuntimeError(
            f"No hay suficientes palabras ({len(candidates)}) para el nivel {config.nombre}."
        )
    rng.shuffle(candidates)
    chosen: list[str] = []
    used: set[str] = set()
    for word in candidates:
        if word in used:
            continue
        chosen.append(word)
        used.add(word)
        if len(chosen) >= config.word_count:
            break
    return sorted(chosen)


# Generador de sopa


def fits(grid: list[list[str]], word: str, row: int, col: int, dr: int, dc: int) -> bool:
    size = len(grid)
    for i, letter in enumerate(word):
        r = row + dr * i
        c = col + dc * i
        if not (0 <= r < size and 0 <= c < size):
            return False
        cell = grid[r][c]
        if cell != " " and cell != letter:
            return False
    return True


def place_word(
    grid: list[list[str]], word: str, row: int, col: int, dr: int, dc: int
) -> None:
    for i, letter in enumerate(word):
        r = row + dr * i
        c = col + dc * i
        grid[r][c] = letter


def try_place_word(
    grid: list[list[str]],
    word: str,
    directions: tuple[tuple[int, int], ...],
    rng: random.Random,
) -> Placement | None:
    size = len(grid)
    positions = [(r, c) for r in range(size) for c in range(size)]
    rng.shuffle(positions)
    dirs = list(directions)
    rng.shuffle(dirs)
    for dr, dc in dirs:
        for row, col in positions:
            if fits(grid, word, row, col, dr, dc):
                place_word(grid, word, row, col, dr, dc)
                return Placement(word=word, row=row, col=col, dr=dr, dc=dc)
    return None


def fill_empty(grid: list[list[str]], rng: random.Random) -> None:
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            if cell == " ":
                grid[r][c] = rng.choice(SPANISH_LETTERS_WEIGHTED)


def generate_puzzle(
    dictionary: list[str],
    nivel: str,
    rng: random.Random | None = None,
) -> Puzzle:
    if nivel not in NIVELES:
        raise ValueError(f"Nivel desconocido: {nivel}. Opciones: {', '.join(NIVELES)}")
    config = NIVELES[nivel]
    rng = rng or random.Random()

    words = pick_words(dictionary, config, rng)
    rng.shuffle(words)

    for attempt in range(config.max_attempts):
        grid = [[" " for _ in range(config.grid_size)] for _ in range(config.grid_size)]
        placements: list[Placement] = []
        ordered = words.copy()
        rng.shuffle(ordered)
        failed = False
        for word in ordered:
            placement = try_place_word(grid, word, config.directions, rng)
            if placement is None:
                failed = True
                break
            placements.append(placement)
        if not failed:
            fill_empty(grid, rng)
            return Puzzle(
                nivel=config,
                grid=grid,
                placements=placements,
                words=sorted(w.word for w in placements),
            )

    raise RuntimeError(
        f"No se pudo generar la sopa ({config.word_count} palabras, "
        f"{config.grid_size}×{config.grid_size}). Probá otra semilla."
    )


# PDF

PAGE_W, PAGE_H = A4
MARGIN = 12 * mm
BORDER_W = 1.2
GRID_BORDER_W = 1.5
INNER_PAD = 3 * mm
HEADER_H = 20 * mm
SECTION_GAP = 5 * mm
FOOTER_H = 8 * mm
LIST_TITLE_H = 10 * mm
LIST_ROW_H = 5.5 * mm


def _draw_rect_border(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    line_w: float = BORDER_W,
) -> None:
    c.setStrokeColor(colors.HexColor("#1e293b"))
    c.setLineWidth(line_w)
    c.rect(x, y, w, h, stroke=1, fill=0)


def _word_list_layout(words: list[str], panel_w: float) -> tuple[int, float]:
    """Elige columnas y calcula la altura del panel de palabras."""
    inner_w = panel_w - 2 * INNER_PAD
    font_name = "Helvetica"
    font_size = 9

    for cols in (5, 4, 3, 2):
        col_w = inner_w / cols
        fits = True
        for word in words:
            text_w = pdfmetrics.stringWidth(f"• {word}", font_name, font_size)
            if text_w > col_w - 1 * mm:
                fits = False
                break
        if fits:
            rows = (len(words) + cols - 1) // cols
            panel_h = LIST_TITLE_H + rows * LIST_ROW_H + 2 * INNER_PAD
            return cols, panel_h

    rows = len(words)
    panel_h = LIST_TITLE_H + rows * LIST_ROW_H + 2 * INNER_PAD
    return 1, panel_h


def render_pdf(puzzle: Puzzle, output: Path, titulo: str | None = None) -> None:
    config = puzzle.nivel
    size = config.grid_size
    words = puzzle.words

    c = canvas.Canvas(str(output), pagesize=A4)

    usable_w = PAGE_W - 2 * MARGIN
    usable_h = PAGE_H - 2 * MARGIN

    outer_x = MARGIN
    outer_y = MARGIN
    outer_w = usable_w
    outer_h = usable_h
    top_y = outer_y + outer_h

    list_panel_w = outer_w - 2 * INNER_PAD
    list_cols, list_panel_h = _word_list_layout(words, list_panel_w)

    reserved_h = HEADER_H + SECTION_GAP + list_panel_h + SECTION_GAP + FOOTER_H
    grid_outer_size = min(outer_w - 2 * INNER_PAD, usable_h - reserved_h)
    cell_size = (grid_outer_size - 2 * INNER_PAD) / size
    grid_draw_size = cell_size * size
    grid_outer_size = grid_draw_size + 2 * INNER_PAD

    _draw_rect_border(c, outer_x, outer_y, outer_w, outer_h, BORDER_W)

    title = titulo or f"Sopa de letras — Nivel {config.titulo}"
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 16)
    c.drawString(outer_x + INNER_PAD, top_y - 9 * mm, title)

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawString(
        outer_x + INNER_PAD,
        top_y - 15 * mm,
        f"Encontrá {len(words)} palabras escondidas (horizontal, vertical y diagonal).",
    )

    grid_x = outer_x + (outer_w - grid_outer_size) / 2
    grid_y = top_y - HEADER_H - SECTION_GAP - grid_outer_size
    _draw_rect_border(c, grid_x, grid_y, grid_outer_size, grid_outer_size, GRID_BORDER_W)

    origin_x = grid_x + INNER_PAD
    origin_y = grid_y + INNER_PAD
    letter_font_size = max(7, min(12, int(cell_size * 0.44)))
    c.setFont("Helvetica-Bold", letter_font_size)

    for r in range(size):
        for col in range(size):
            letter = puzzle.grid[r][col]
            cx = origin_x + col * cell_size + cell_size / 2
            cy = origin_y + (size - 1 - r) * cell_size + cell_size / 2
            c.setStrokeColor(colors.HexColor("#cbd5e1"))
            c.setLineWidth(0.4)
            c.rect(
                origin_x + col * cell_size,
                origin_y + (size - 1 - r) * cell_size,
                cell_size,
                cell_size,
                stroke=1,
                fill=0,
            )
            c.setFillColor(colors.HexColor("#0f172a"))
            c.drawCentredString(cx, cy - letter_font_size * 0.35, letter)

    list_x = outer_x + INNER_PAD
    list_y = grid_y - SECTION_GAP - list_panel_h
    _draw_rect_border(c, list_x, list_y, list_panel_w, list_panel_h, GRID_BORDER_W)

    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 11)
    c.drawString(list_x + INNER_PAD, list_y + list_panel_h - 7 * mm, "Palabras a buscar")

    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setLineWidth(0.6)
    c.line(
        list_x + INNER_PAD,
        list_y + list_panel_h - 9 * mm,
        list_x + list_panel_w - INNER_PAD,
        list_y + list_panel_h - 9 * mm,
    )

    c.setFont("Helvetica", 9)
    col_w = (list_panel_w - 2 * INNER_PAD) / list_cols
    start_y = list_y + list_panel_h - LIST_TITLE_H - 2 * mm

    for idx, word in enumerate(words):
        col_idx = idx % list_cols
        row_idx = idx // list_cols
        wx = list_x + INNER_PAD + col_idx * col_w
        wy = start_y - row_idx * LIST_ROW_H
        c.drawString(wx, wy, f"• {word}")

    c.setFont("Helvetica-Oblique", 7.5)
    c.setFillColor(colors.HexColor("#64748b"))
    c.drawString(
        outer_x + INNER_PAD,
        outer_y + 3 * mm,
        "Generado con wordsworld.py — imprimí y ¡a buscar!",
    )

    c.showPage()
    c.save()
    print(f"PDF generado: {output}")


# CLI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Genera sopas de letras en español en PDF A4.",
    )
    parser.add_argument(
        "--nivel",
        choices=list(NIVELES.keys()),
        default="medio",
        help="Nivel de dificultad (default: medio)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Archivo PDF de salida (default: sopa-<nivel>.pdf)",
    )
    parser.add_argument(
        "--semilla",
        type=int,
        default=None,
        help="Semilla aleatoria para reproducir la misma sopa",
    )
    parser.add_argument(
        "--diccionario",
        type=Path,
        default=DEFAULT_DICT_PATH,
        help=f"Ruta al archivo de palabras (default: {DEFAULT_DICT_PATH})",
    )
    parser.add_argument(
        "--descargar-diccionario",
        action="store_true",
        help="Solo descarga/actualiza el diccionario y termina",
    )
    parser.add_argument(
        "--titulo",
        default=None,
        help="Título personalizado en el PDF",
    )
    parser.add_argument(
        "--sin-descarga",
        action="store_true",
        help="No intentar descargar el diccionario si falta",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.descargar_diccionario:
        download_dictionary(args.diccionario)
        return 0

    output = args.output or Path(f"sopa-{args.nivel}.pdf")
    rng = random.Random(args.semilla)

    dictionary = load_dictionary(args.diccionario, auto_download=not args.sin_descarga)
    puzzle = generate_puzzle(dictionary, args.nivel, rng)
    render_pdf(puzzle, output, titulo=args.titulo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
