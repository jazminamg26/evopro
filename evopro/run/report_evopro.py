# report_evopro_flex.py
# Uso:
#   1) Coloca este script en la carpeta donde está scores.csv (o ajusta PATH).
#   2) python report_evopro_flex.py
#   3) Revisa la carpeta "report_assets/"

# import os, re, csv, sys
# import pandas as pd

# # Evita dependencias de GUI en matplotlib (funciona en servidores/headless)
# import matplotlib
# matplotlib.use("Agg")
# import matplotlib.pyplot as plt

# # ---------- Config ----------
# PATH = "/home/david/Documents/Dev/Tesis/evopro/evopro/run/outputs/scores.csv"       # Cambia si lo necesitas
# OUT  = "r/home/david/Documents/Dev/Tesis/evopro/evopro/run/outputs/"    # Carpeta de salida
# TOPN = 10                 # Tamaño del Top-N para la tabla

# os.makedirs(OUT, exist_ok=True)

# # ---------- Utilidades ----------
# def _is_number(tok: str) -> bool:
#     try:
#         float(tok.strip())
#         return True
#     except Exception:
#         return False

# def _clean_token(tok: str) -> str:
#     # elimina separadores " | " y espacios extra
#     return re.sub(r"\s*\|\s*", "", tok).strip()

# # ---------- Lector robusto de scores.csv ----------
# def load_evopro_scores_flex(path: str) -> pd.DataFrame:
#     # Lee todo como texto (soporta rarezas del CSV)
#     with open(path, "r", encoding="utf-8", errors="ignore") as f:
#         lines = [ln.rstrip("\n") for ln in f]

#     # 1) Encuentra la fila de encabezados "reales" (la que contiene overall_score)
#     header_idx = None
#     for i, ln in enumerate(lines[:300]):
#         if "overall_score" in ln:
#             header_idx = i
#             break
#     if header_idx is None:
#         raise RuntimeError("No encontré la línea de encabezados con 'overall_score'.")

#     # Parseo de la cabecera con csv.reader (respeta comillas, etc.)
#     header_tokens = [t.strip() for t in next(csv.reader([lines[header_idx]]))]
#     # índice donde empiezan las métricas (todo lo previo suelen ser columnas de secuencia/espaciadores)
#     try:
#         start_header = header_tokens.index("overall_score")
#     except ValueError:
#         start_header = next(i for i, t in enumerate(header_tokens) if "overall_score" in t)

#     metric_cols = [t for t in header_tokens[start_header:] if t != ""]
#     n_metrics   = len(metric_cols)
#     if n_metrics < 4:
#         raise RuntimeError(f"Cabecera con pocas métricas ({n_metrics}). Tokens: {header_tokens}")

#     records = []
#     # 2) Recorre las filas de datos
#     for j in range(header_idx + 1, len(lines)):
#         ln = lines[j].strip()
#         if not ln:
#             continue
#         if "overall_score" in ln or ln.startswith("Iteration"):
#             # re-aparición de cabecera o marcador de iteración
#             continue

#         # Limpia separadores raros y trocea seguro
#         ln = _clean_token(ln)
#         parts = next(csv.reader([ln]))

#         # Quita vacíos al final y espaciadores internos vacíos
#         parts = [p for p in parts if p != ""]
#         if not parts:
#             continue

#         # Detecta cuántas columnas iniciales son NO numéricas → normalmente 2 (seqA, seqB)
#         n_seq_cols = 0
#         for tok in parts:
#             if _is_number(tok):
#                 break
#             n_seq_cols += 1

#         if n_seq_cols < 1:
#             # No hay secuencias; fila sospechosa
#             continue

#         seq_cols = parts[:n_seq_cols]
#         remain   = parts[n_seq_cols:]

#         # ¿Cuántos bloques de pred hay? (preds = 1 o 2 normalmente)
#         preds = len(remain) // n_metrics
#         if preds == 0:
#             # quizá la fila está incompleta; intenta truncar a un bloque completo si hay > n_metrics
#             if len(remain) >= n_metrics:
#                 preds = 1
#             else:
#                 continue
#         remain = remain[:preds * n_metrics]  # recorta a múltiplo exacto

#         # Secuencias (toma las dos primeras si existen)
#         seqA = seq_cols[0] if len(seq_cols) >= 1 else f"seq_{j}"
#         seqB = seq_cols[1] if len(seq_cols) >= 2 else ""

#         # Crea un registro por pred
#         for p in range(preds):
#             seg = remain[p * n_metrics : (p + 1) * n_metrics]
#             rec = {"seqA": seqA, "seqB": seqB, "pred": p + 1}
#             for k, colname in enumerate(metric_cols):
#                 rec[colname] = seg[k] if k < len(seg) else ""
#             records.append(rec)

#     df = pd.DataFrame.from_records(records)

#     # 3) Limpia tipos numéricos (mantén seqA/seqB como texto)
#     for c in df.columns:
#         if c in ("seqA", "seqB"):
#             continue
#         df[c] = pd.to_numeric(df[c].astype(str).str.strip(), errors="coerce")

#     # 4) Normaliza nombres clave (por si luego cambian el orden en el CSV)
#     rename_map = {
#         "overall_score": "overall_score",
#         "pLDDT_chainA": "pLDDT_chainA",
#         "ipTM": "ipTM",
#         "ContactScore": "ContactScore",
#         "ConfDiffScore": "ConfDiffScore",
#     }
#     have = {k: v for k, v in rename_map.items() if k in df.columns}
#     df = df.rename(columns=have)

#     # ID corto para visualización
#     df["sequence_id"] = df["seqA"].astype(str).str.slice(0, 12) + "..."
#     return df

# # ---------- Carga y ranking ----------
# df_long = load_evopro_scores_flex(PATH)
# if df_long.empty:
#     print("No se obtuvieron filas de datos. Revisa el CSV.", file=sys.stderr)
#     sys.exit(1)

# # Asegura que exista overall_score
# if "overall_score" not in df_long.columns:
#     raise RuntimeError("No encontré la columna 'overall_score' después del parseo.")

# # Elige el MEJOR pred por secuencia (mínimo overall_score)
# idx = df_long.groupby("seqA", sort=False)["overall_score"].idxmin()
# best = df_long.loc[idx].copy()

# # Orden global (más negativo = mejor)
# best = best.sort_values("overall_score", ascending=True)

# # Columnas clave si existen
# key_cols = [c for c in ["overall_score","pLDDT_chainA","ipTM","ContactScore","ConfDiffScore"] if c in best.columns]
# display_cols = ["sequence_id","pred"] + key_cols

# # ---------- Exporta Top-N ----------
# top = best.nsmallest(TOPN, "overall_score")[display_cols].copy()
# top.to_csv(os.path.join(OUT, "top_designs.csv"), index=False)

# # PNG de tabla para pegar en slides
# fig, ax = plt.subplots(figsize=(10, 0.6 + 0.5*len(top)))
# ax.axis("off")
# tbl = ax.table(cellText=top.round(3).values,
#                colLabels=top.columns.tolist(),
#                loc="center")
# tbl.auto_set_font_size(False); tbl.set_fontsize(9)
# for _, cell in tbl.get_celld().items():
#     cell.set_height(0.065)
# fig.tight_layout()
# plt.savefig(os.path.join(OUT, "top_designs.png"), dpi=220)

# # ---------- Gráficos (solo si hay columnas requeridas) ----------
# # a) ipTM vs ContactScore
# if all(c in best.columns for c in ["ipTM","ContactScore"]):
#     plt.figure(figsize=(6,4))
#     plt.scatter(best["ipTM"], best["ContactScore"])
#     plt.xlabel("ipTM"); plt.ylabel("ContactScore")
#     plt.title("ipTM vs ContactScore (mejor pred por secuencia)")
#     plt.tight_layout()
#     plt.savefig(os.path.join(OUT, "iptm_vs_contact.png"), dpi=220)

# # b) pLDDT (monómero) vs ConfDiff (RMSD-like)
# if all(c in best.columns for c in ["pLDDT_chainA","ConfDiffScore"]):
#     plt.figure(figsize=(6,4))
#     plt.scatter(best["pLDDT_chainA"], best["ConfDiffScore"])
#     plt.xlabel("pLDDT_chainA"); plt.ylabel("ConfDiffScore")
#     plt.title("Fold vs Conformacional (mejor pred por secuencia)")
#     plt.tight_layout()
#     plt.savefig(os.path.join(OUT, "plddt_vs_confdiff.png"), dpi=220)

# # ---------- Mensaje final ----------
# print("OK. Generé:")
# print(" -", os.path.join(OUT, "top_designs.csv"))
# print(" -", os.path.join(OUT, "top_designs.png"))
# if all(c in best.columns for c in ["ipTM","ContactScore"]):
#     print(" -", os.path.join(OUT, "iptm_vs_contact.png"))
# if all(c in best.columns for c in ["pLDDT_chainA","ConfDiffScore"]):
#     print(" -", os.path.join(OUT, "plddt_vs_confdiff.png"))



# bundle_evopro_for_slides.py
# Empaqueta PNG/CSV/PDB y arma una galería HTML simple.
import os, shutil, glob, zipfile, html
ROOT = "."                      # carpeta donde está scores.csv
OUT = "evopro_share_bundle"
IMG_DIR = os.path.join(OUT, "figures")
TAB_DIR = os.path.join(OUT, "tables")
STR_DIR = os.path.join(OUT, "structures")
os.makedirs(IMG_DIR, exist_ok=True); os.makedirs(TAB_DIR, exist_ok=True); os.makedirs(STR_DIR, exist_ok=True)

# Copia CSV y tablas si existen
for f in ["scores.csv", "report_assets/top_designs.csv"]:
    if os.path.exists(f): shutil.copy(f, TAB_DIR)

# Copia figuras comunes
for pattern in [
    "report_assets/*.png",
    "./**/*.png",  # toma pLDDT/PAE y otras figuras
]:
    for f in glob.glob(pattern, recursive=True):
        # Evita duplicar thumbs temporales:
        if any(s in f.lower() for s in ["__pycache__", ".ipynb_checkpoints"]): 
            continue
        # Nombre simple
        base = os.path.basename(f)
        # Evita choques: si existe, agrega sufijo incremental
        dest = os.path.join(IMG_DIR, base)
        i=1
        while os.path.exists(dest):
            name, ext = os.path.splitext(base)
            dest = os.path.join(IMG_DIR, f"{name}_{i}{ext}")
            i+=1
        shutil.copy(f, dest)

# Copia estructuras si las quieres compartir
for ext in ("*.pdb","*.cif","*.mmcif"):
    for f in glob.glob(f"./**/{ext}", recursive=True):
        shutil.copy(f, os.path.join(STR_DIR, os.path.basename(f)))

# Galería HTML
imgs = sorted(os.listdir(IMG_DIR))
rows = []
for im in imgs:
    rows.append(f"""
    <figure style="margin:12px; display:inline-block; text-align:center">
      <img src="figures/{html.escape(im)}" style="max-width:420px; height:auto; display:block; border:1px solid #ddd; border-radius:8px; padding:6px;">
      <figcaption style="font:14px/1.3 system-ui, sans-serif; color:#444">{html.escape(im)}</figcaption>
    </figure>""")
html_doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>EvoPro bundle</title></head>
<body style="margin:24px; font:16px/1.4 system-ui, sans-serif">
<h1 style="margin:0 0 8px">EvoPro – Figuras y Tablas</h1>
<p>Abre este archivo en el navegador y presenta en pantalla completa. Las imágenes están en <code>figures/</code>.</p>
<h2>Tablas</h2>
<ul>
  <li><a href="tables/top_designs.csv">top_designs.csv</a></li>
  <li><a href="tables/scores.csv">scores.csv</a></li>
</ul>
<h2>Figuras</h2>
{''.join(rows) if rows else '<p>(Agrega PNGs a la carpeta figures/)</p>'}
</body></html>"""
with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
    fh.write(html_doc)

# ZIP final
zip_path = OUT + ".zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for folder, _, files in os.walk(OUT):
        for f in files:
            full = os.path.join(folder, f)
            zf.write(full, os.path.relpath(full, OUT))
print("Listo:", zip_path)

