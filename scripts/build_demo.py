from __future__ import annotations

import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from routools.csv_report import build_report as csv_report
from routools.dedupe import apply_quarantine, find_duplicates, report as dedupe_report
from routools.rename import apply_plan, build_plan, report as rename_report

DEMO = ROOT / "demo"
WORK = DEMO / "work"
QUARANTINE = DEMO / "quarantine"


def rel(value: str) -> str:
    return str(Path(value).resolve().relative_to(ROOT))


def main() -> None:
    if WORK.exists():
        shutil.rmtree(WORK)
    if QUARANTINE.exists():
        shutil.rmtree(QUARANTINE)
    WORK.mkdir(parents=True)
    for source in (ROOT / "examples" / "files").iterdir():
        if source.is_file():
            shutil.copy2(source, WORK / source.name)

    groups = find_duplicates(WORK)
    dedupe_data = dedupe_report(groups)
    moved = apply_quarantine(groups, QUARANTINE)
    dedupe_data["moved"] = len(moved)

    plans = build_plan(WORK, "doc_{n:03d}{suffix}")
    apply_plan(plans)
    rename_data = rename_report(plans)
    rename_data["applied"] = True

    csv_data = csv_report(ROOT / "examples" / "invoices.csv")

    for item in dedupe_data["items"]:
        item["keep"] = rel(item["keep"])
        item["duplicates"] = [rel(path) for path in item["duplicates"]]
    for item in rename_data["items"]:
        item["source"] = rel(item["source"])
        item["target"] = rel(item["target"])
    csv_data["file"] = rel(csv_data["file"])

    result = {
        "dedupe": dedupe_data,
        "rename": rename_data,
        "csv": csv_data,
    }
    (DEMO / "report.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (DEMO / "index.html").write_text(render(result), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def render(data: dict) -> str:
    dedupe = data["dedupe"]
    rename = data["rename"]
    csv_data = data["csv"]
    duplicate_rows = "".join(
        f"<tr><td>{html.escape(item['keep'])}</td><td>{html.escape(', '.join(item['duplicates']))}</td></tr>"
        for item in dedupe["items"]
    )
    rename_rows = "".join(
        f"<tr><td>{html.escape(item['source'])}</td><td>{html.escape(item['target'])}</td></tr>"
        for item in rename["items"]
    )
    columns = ", ".join(html.escape(column) for column in csv_data["columns"])
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>routools — демо</title>
<style>
:root {{ color-scheme: dark; --bg:#0b0c0f; --panel:#14171d; --line:#2a2f39; --text:#f2efe8; --muted:#a7a9af; --gold:#e9b949; --blue:#6ea8fe; --green:#78d6a4; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:radial-gradient(circle at 10% 0%,rgba(233,185,73,.12),transparent 34rem),var(--bg); color:var(--text); font:15px/1.55 Inter,"Segoe UI",system-ui,sans-serif; }}
main {{ width:min(calc(100% - 40px),1000px); margin:auto; padding:56px 0; }}
.eyebrow {{ margin:0 0 10px; color:var(--gold); font-size:12px; font-weight:800; letter-spacing:.16em; text-transform:uppercase; }}
h1 {{ margin:0 0 12px; font-size:clamp(36px,6vw,66px); line-height:.98; letter-spacing:-.05em; }}
.lead {{ max-width:720px; color:var(--muted); font-size:18px; }}
.stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin:28px 0; }}
.stat {{ padding:16px; border:1px solid var(--line); border-radius:14px; background:var(--panel); }}
.stat span {{ display:block; color:var(--muted); font-size:12px; }}
.stat strong {{ font-size:26px; }}
.panel {{ margin:12px 0; padding:20px; border:1px solid var(--line); border-radius:16px; background:var(--panel); }}
.panel h2 {{ margin:0 0 10px; font-size:18px; }}
.panel p {{ margin:0 0 12px; color:var(--muted); }}
code, pre {{ font-family:"Cascadia Code",Consolas,monospace; }}
pre {{ margin:0; padding:12px; overflow:auto; border:1px solid var(--line); border-radius:10px; background:#0d1015; color:var(--green); font-size:12px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th,td {{ padding:9px 8px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
th {{ color:var(--muted); font-weight:600; }}
td:first-child {{ color:var(--blue); }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
.footer {{ margin-top:26px; color:#777b84; font-size:12px; }}
@media (max-width:720px) {{ .stats,.grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body><main>
<p class="eyebrow">routools · demo report</p>
<h1>Рутина, которую можно проверить</h1>
<p class="lead">Три команды на тестовых данных: поиск дублей, безопасное переименование и отчёт по CSV. Все изменения сначала показываются как план.</p>
<div class="stats">
  <div class="stat"><span>дублей найдено</span><strong>{dedupe['duplicates']}</strong></div>
  <div class="stat"><span>перемещено</span><strong>{dedupe['moved']}</strong></div>
  <div class="stat"><span>файлов переименовано</span><strong>{rename['files']}</strong></div>
  <div class="stat"><span>строк CSV</span><strong>{csv_data['rows']}</strong></div>
</div>
<div class="grid">
  <section class="panel"><h2>1. Дубли</h2><p>SHA-256 + размер, без чтения лишних файлов.</p><pre>python -m routools dedupe demo/work --apply --quarantine demo/quarantine</pre></section>
  <section class="panel"><h2>2. Переименование</h2><p>Сортировка, проверка коллизий, dry-run по умолчанию.</p><pre>python -m routools rename demo/work --pattern "doc_{{n:03d}}{{suffix}}" --apply</pre></section>
</div>
<section class="panel"><h2>Дубли</h2><table><thead><tr><th>Оставлен</th><th>Перемещён</th></tr></thead><tbody>{duplicate_rows}</tbody></table></section>
<section class="panel"><h2>Переименование</h2><table><thead><tr><th>Было</th><th>Стало</th></tr></thead><tbody>{rename_rows}</tbody></table></section>
<section class="panel"><h2>CSV-отчёт</h2><p>Колонки: {columns}</p><pre>rows: {csv_data['rows']}
blank_rows: {csv_data['blank_rows']}
duplicate_rows: {csv_data['duplicate_rows']}
empty_cells: {csv_data['empty_cells']}</pre></section>
<p class="footer">Демо на тестовых данных. В репозитории нет клиентских файлов и секретов.</p>
</main></body></html>
"""


if __name__ == "__main__":
    main()
