#!/usr/bin/env python3
# netsuite_extract_pos.py — extrai Purchase Orders (notas de encomenda) do NetSuite
# via SuiteQL REST + TBA (Token-Based Auth) e grava CSV no formato aceite pelo
# SNT CMT (Producao > Carregar POs). Agendar (cron / Task Scheduler) para
# alimentacao automatica — substitui o carregamento manual.
#
#   pip install requests requests-oauthlib
#   export NS_ACCOUNT=1234567 NS_CONSUMER_KEY=... NS_CONSUMER_SECRET=...
#   export NS_TOKEN_ID=... NS_TOKEN_SECRET=...
#   python3 netsuite_extract_pos.py pos_garment.csv
import os, sys, csv, requests
from requests_oauthlib import OAuth1

ACCOUNT = os.environ["NS_ACCOUNT"].replace("-", "_")
BASE = "https://%s.suitetalk.api.netsuite.com/services/rest/query/v1/suiteql" % ACCOUNT.lower()

AUTH = OAuth1(os.environ["NS_CONSUMER_KEY"], os.environ["NS_CONSUMER_SECRET"],
              os.environ["NS_TOKEN_ID"], os.environ["NS_TOKEN_SECRET"],
              signature_method="HMAC-SHA256", realm=os.environ["NS_ACCOUNT"])

# Ajusta os campos custom (custcol_*) ao teu account — ver Setup > SuiteQL.
QUERY = """
SELECT t.tranid AS po_number,
       i.itemid AS model_name,
       e.entityid AS confeccionador,
       tl.quantity AS po_qty,
       BUILTIN.DF(tl.custcol_snt_fabric_ref) AS fabric_ref,
       BUILTIN.DF(tl.custcol_snt_color) AS color,
       tl.custcol_snt_metres AS metres_expected,
       t.duedate AS expected_date
FROM transaction t
JOIN transactionline tl ON tl.transaction = t.id
LEFT JOIN item i ON i.id = tl.item
LEFT JOIN entity e ON e.id = t.entityid
WHERE t.type = 'PurchOrd' AND tl.mainline = 'F' AND tl.item IS NOT NULL
"""

def run():
    out = sys.argv[1] if len(sys.argv) > 1 else "pos_garment.csv"
    rows, url = [], BASE
    payload = {"q": QUERY}
    while url:
        r = requests.post(url, auth=AUTH, json=payload,
                          headers={"Prefer": "transient"}, timeout=60)
        r.raise_for_status()
        data = r.json()
        rows.extend(data.get("items", []))
        url = next((l["href"] for l in data.get("links", []) if l.get("rel") == "next"), None)
        payload = {"q": QUERY}
    cols = ["po_number", "model_name", "confeccionador", "po_qty", "fabric_ref",
            "color", "metres_expected", "expected_date", "status"]
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            r["status"] = "PENDING"
            w.writerow({c: r.get(c, "") for c in cols})
    print("OK — %d linhas -> %s" % (len(rows), out))

if __name__ == "__main__":
    run()
