"""Arma recorrido/index.html con la geometría embebida. Uso: python3 tools/build_recorrido.py"""
import json, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
casa = json.loads((root / "recorrido/casa.json").read_text())
tpl = (root / "tools/recorrido.template.html").read_text()
(root / "recorrido/index.html").write_text(tpl.replace("/*CASA*/null", json.dumps(casa, separators=(",", ":"))))
print("ok")
