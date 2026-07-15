#!/usr/bin/env python3
"""
align_cross_lingual.py — #7 cross-lingual statement alignment (PROPOSE stage).

Both statement CSVs already carry an English rendering (`statement_en`), so the
cross-lingual match collapses to English-vs-English semantic similarity. We embed
every statement locally (sentence-transformers, CPU) and, for each SRC statement,
propose its top-k TGT candidates by cosine. Output is a *review table* — proposals
to be human-confirmed, NOT gold. Cross-wiki pairs record equivalence, never merge.

Run (ephemeral env, no project install):
  uv run --python 3.12 --with sentence-transformers python net/align_cross_lingual.py \
      --src data/exploration/runs/de__wikipedia_neutraler_standpunkt.statements.csv \
      --tgt data/exploration/runs/en__wikipedia_neutral_point_of_view.statements.csv \
      --out data/exploration/runs/align_de_en_npov

Thresholds below are PROVISIONAL (MiniLM cosine bands) and must be calibrated on
the confirmed sample before any formal claim.
"""
from __future__ import annotations
import argparse, csv, sys
from pathlib import Path

TAU_HIGH = 0.70   # >= -> propose "equivalent"        (PROVISIONAL)
TAU_LOW  = 0.45   # <  -> propose "none" (divergence)  (PROVISIONAL)
TOPK     = 3
MODEL    = "sentence-transformers/all-MiniLM-L6-v2"


def load(path: Path) -> list[dict]:
    rows = list(csv.DictReader(path.open()))
    for r in rows:
        r["_en"] = (r.get("statement_en") or "").strip()
    missing = [r["statement_id"] for r in rows if not r["_en"]]
    if missing:
        print(f"  WARN: {len(missing)} rows in {path.name} have empty statement_en: {missing[:5]}",
              file=sys.stderr)
    return rows


def band(score: float) -> str:
    if score >= TAU_HIGH: return "equivalent"
    if score <  TAU_LOW:  return "none"
    return "review"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, type=Path, help="source statements.csv (e.g. de)")
    ap.add_argument("--tgt", required=True, type=Path, help="target statements.csv (e.g. en)")
    ap.add_argument("--out", required=True, type=Path, help="output prefix (no extension)")
    args = ap.parse_args()

    import numpy as np
    from sentence_transformers import SentenceTransformer

    src, tgt = load(args.src), load(args.tgt)
    print(f"  src={len(src)}  tgt={len(tgt)}  model={MODEL}")

    model = SentenceTransformer(MODEL)
    emb = model.encode([r["_en"] for r in src] + [r["_en"] for r in tgt],
                       normalize_embeddings=True, show_progress_bar=False)
    E_src, E_tgt = np.asarray(emb[:len(src)]), np.asarray(emb[len(src):])
    sim = E_src @ E_tgt.T                        # (n_src, n_tgt) cosine, both normalized

    # --- SRC -> top-k TGT proposals (the review table) ---
    out_csv = args.out.with_suffix(".csv")
    counts = {"equivalent": 0, "review": 0, "none": 0}
    with out_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["src_id", "src_statement_en", "proposed_label", "best_tgt_id",
                    "best_score", "best_tgt_statement_en",
                    "cand2_id", "cand2_score", "cand3_id", "cand3_score", "confirmed?"])
        for i, r in enumerate(src):
            order = np.argsort(-sim[i])[:TOPK]
            best = int(order[0]); bscore = float(sim[i, best])
            lab = band(bscore); counts[lab] += 1
            row = [r["statement_id"], r["_en"], lab, tgt[best]["statement_id"],
                   f"{bscore:.3f}", tgt[best]["_en"]]
            for j in list(order[1:]) + [None] * (TOPK - 1 - len(order[1:])):
                if j is None: row += ["", ""]
                else:         row += [tgt[int(j)]["statement_id"], f"{float(sim[i,int(j)]):.3f}"]
            row.append("")   # confirmed? — human fills: y / n / partial
            w.writerow(row)

    # --- TGT norms with NO good src match = divergence (tgt-only) ---
    tgt_best = sim.max(axis=0)                    # best src score per tgt norm
    orphans = [(tgt[j]["statement_id"], float(tgt_best[j]), tgt[j]["_en"])
               for j in range(len(tgt)) if tgt_best[j] < TAU_LOW]
    orphans.sort(key=lambda x: x[1])
    orph_csv = args.out.parent / (args.out.name + "_tgt_only.csv")
    with orph_csv.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tgt_id", "best_src_score", "tgt_statement_en"])
        w.writerows(orphans)

    print(f"  proposals: equivalent={counts['equivalent']}  "
          f"review={counts['review']}  none={counts['none']}")
    print(f"  tgt-only (score<{TAU_LOW}): {len(orphans)} of {len(tgt)} target norms")
    print(f"  wrote {out_csv}")
    print(f"  wrote {orph_csv}")
    print(f"  NOTE thresholds PROVISIONAL (TAU_HIGH={TAU_HIGH}, TAU_LOW={TAU_LOW}) — calibrate on review.")


if __name__ == "__main__":
    main()
