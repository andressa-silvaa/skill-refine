"""
Aritmética de data e sorteio de bullets para o seed sintético.
"""
from __future__ import annotations

import calendar
import random
from datetime import date

from .synthetic_seed_data import BULLET_BANK


def add_months(d: date, delta_m: int) -> date:
    y, m = d.year, d.month + delta_m
    while m > 12:
        y += 1
        m -= 12
    while m < 1:
        y -= 1
        m += 12
    last = calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, last))


def _ym(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _bullet_bank(rng: random.Random) -> list[str]:
    opts = list(BULLET_BANK)
    rng.shuffle(opts)
    return opts
