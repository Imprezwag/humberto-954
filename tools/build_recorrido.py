"""Arma recorrido/index.html con la geometría embebida. Uso: python3 tools/build_recorrido.py [carpeta plantilla]  (v2: recorrido-v2 tools/recorrido_v2.template.html)"""
import json, pathlib, sys
DIR, TPL = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("recorrido", "tools/recorrido.template.html")
root = pathlib.Path(__file__).resolve().parent.parent
casa = json.loads((root / DIR / "casa.json").read_text())
tpl = (root / TPL).read_text()
(root / DIR / "index.html").write_text(tpl.replace("/*CASA*/null", json.dumps(casa, separators=(",", ":"))))
print("ok")
