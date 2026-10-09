#!/usr/bin/env python3
"""Build static Rigs metadata JSON.

Inputs:
  --tableland-db   artifacts/tableland.db from tablelandnetwork/rigs (rigs, rig_attributes, deals, lookups)
  --inflight       JSON list of Rig IDs with an open pilot session (snapshot of pilot_sessions_1_7)
  --base-url       Public URL the static site will be served from (no trailing slash)
  --out            Output directory; writes metadata/<id>.json and contract.json

Mirrors the live Tableland tokenURI query (ethereum/helpers/uris.ts, displayAttributes=true)
with these changes: image points at <base>/images/<id>.jpg, external_url points at <base>/?rig=<id>,
and animation_url and the IPFS-only image fields are dropped.
"""
import argparse, json, os, sqlite3

p = argparse.ArgumentParser()
p.add_argument("--tableland-db", required=True)
p.add_argument("--inflight", required=True)
p.add_argument("--base-url", required=True)
p.add_argument("--out", required=True)
a = p.parse_args()
base = a.base_url.rstrip("/")

db = sqlite3.connect(a.tableland_db)
lookups = dict(db.execute("select label, value from lookups"))
filecoin_base = lookups["filecoin_base_url"]
inflight = set(json.load(open(a.inflight)))

attrs = {}
for rig_id, display_type, trait_type, value in db.execute(
    "select rig_id, display_type, trait_type, value from rig_attributes"
):
    attrs.setdefault(rig_id, []).append((display_type, trait_type, value))
for rig_id, deal_number, deal_id in db.execute("select rig_id, deal_number, deal_id from deals"):
    attrs.setdefault(rig_id, []).append(("string", f"Filecoin Deal {deal_number}", f"{filecoin_base}{deal_id}"))

os.makedirs(os.path.join(a.out, "metadata"), exist_ok=True)
for (rig_id,) in db.execute("select id from rigs order by id"):
    rows = attrs[rig_id] + [("string", "Garage Status", "in-flight" if rig_id in inflight else "parked")]
    # The live query builds attributes from a SQL UNION, which returns rows sorted
    # by (display_type, trait_type, value); keep that order.
    rows.sort()
    meta = {
        "name": f"Rig #{rig_id} ✈️" if rig_id in inflight else f"Rig #{rig_id}",
        "external_url": f"{base}/?rig={rig_id}",
        "image": f"{base}/images/{rig_id}.jpg",
        "attributes": [{"display_type": d, "trait_type": t, "value": v} for d, t, v in rows],
    }
    with open(os.path.join(a.out, "metadata", f"{rig_id}.json"), "w") as f:
        json.dump(meta, f, ensure_ascii=False, separators=(",", ":"))

# Collection-level metadata (contractURI), values from rigs_contract_42161_12.
contract = {
    "name": "Tableland Rigs",
    "description": "A 3k generative NFT built from 1,074 handcrafted works of art for the builders and creatives of cyberspace.",
    "image": f"{base}/rigs.png",
    "external_link": f"{base}/",
    "seller_fee_basis_points": 500,
    "fee_recipient": "0x9BE9627e25c9f348C1edB6E46dBCa2a6669e2D56",
}
with open(os.path.join(a.out, "contract.json"), "w") as f:
    json.dump(contract, f, ensure_ascii=False, indent=2)
