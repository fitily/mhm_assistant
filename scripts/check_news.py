"""Diagnostic des actualités médicales : que renvoie CHAQUE source, et que devient chaque article avec la période de 7 jours ?

    python scripts/check_news.py

Interroge les vraies sources (aucun secret, aucune base de données). Pour chaque source : joignable ou non, nombre d'articles
lus, dates, et combien restent dans la période / sont trop anciens / sans date / datés du futur, par catégorie.
"""
from __future__ import annotations

import asyncio
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import httpx  # noqa: E402

from app.services import feed_service  # noqa: E402


async def main() -> int:
    start, end = feed_service.news_window()
    print(f"Période affichée : du {start:%d/%m/%Y %H:%M} UTC au {end:%d/%m/%Y %H:%M} UTC\n")
    headers = {"User-Agent": "MHM-Ambovo-Health-News/1.0",
               "Accept": "text/html, application/rss+xml, application/xml;q=0.9, */*;q=0.8"}
    total = Counter()
    async with httpx.AsyncClient(timeout=feed_service._TIMEOUT, follow_redirects=True, headers=headers) as client:
        for src in feed_service._sources():
            print(f"== {src['label']}  ({src['url']})")
            try:
                text = await feed_service._get_text(client, src["url"])
                articles = src["parse"](text)
            except httpx.HTTPStatusError as exc:
                print(f"   ECHEC : la source répond HTTP {exc.response.status_code}\n")
                continue
            except Exception as exc:  # noqa: BLE001
                print(f"   ECHEC : {type(exc).__name__} {str(exc)[:120]}\n")
                continue
            status = Counter()
            dates = []
            images = sum(1 for a in articles if a.get("image"))
            for a in articles:
                published = feed_service._published(a)
                if published is None:
                    status["sans date lisible"] += 1
                    continue
                dates.append(published)
                if published < start:
                    status["trop ancien"] += 1
                elif published > end:
                    status["daté du futur"] += 1
                else:
                    status[f"DANS la période ({a['category']})"] += 1
                    total[a["category"]] += 1
            span = f"{min(dates):%d/%m/%Y} -> {max(dates):%d/%m/%Y}" if dates else "aucune date"
            print(f"   {len(articles)} article(s) lu(s), dates : {span}, avec image : {images}")
            for label, n in sorted(status.items()):
                print(f"   - {label}: {n}")
            if not articles:
                print("   (aucun article reconnu : la structure de la page a peut-être changé)")
            print()
    print("Résultat par onglet (période de 7 jours) :",
          ", ".join(f"{k}={total.get(k, 0)}" for k in ("breaking", "research", "update")))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
