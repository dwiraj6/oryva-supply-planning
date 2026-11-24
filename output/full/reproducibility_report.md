# Reproducibility (full, seed 20261022)

Generated twice with the same seed into separate temporary folders: **IDENTICAL**.  
Matches the committed dataset: **True**.  
Same generator with seed 20261023 produces different files (sanity check).

| File | Rows | SHA-256 (run 1) | Run 2 identical | Matches committed | Differs with seed+1 |
|---|---|---|---|---|---|
| bom.csv | 1504 | `4b20b0da92798e08...` | True | True | True |
| forecast_demand.csv.gz | 501176 | `8e7e549dc2411869...` | True | True | True |
| ground_truth.csv |  | `40d4df7512772718...` | True |  |  |
| inbound_shipment.csv | 3197 | `3330348f868927c9...` | True | True | True |
| inventory.csv | 11735 | `282bff1db3bc7e0c...` | True | True | True |
| lead_time.csv | 13238 | `f2147ef1f8c25ff2...` | True | True | True |
| location.csv | 50 | `77537334781d0534...` | True | True | True |
| po_event.csv.gz | 25424 | `fed037f880f42eae...` | True | True | True |
| production_capacity.csv.gz | 260 | `527f1845a909aa82...` | True | True | True |
| production_plan.csv.gz | 37519 | `428ee72f95db052a...` | True | True | True |
| purchase_order.csv | 10080 | `d3c7d573b485cf3f...` | True | True | True |
| sku.csv | 3000 | `bf2e8f84ee50c150...` | True | True | True |
| sku_location.csv | 11735 | `6979ea203cc81765...` | True | True | True |
| sku_substitute.csv | 471 | `0ff894c0363f143b...` | True | True | True |
| supplier.csv | 500 | `7038df8faaf8cc60...` | True | True | True |
| supplier_capacity.csv.gz | 26000 | `e21a30fe41673e7d...` | True | True | True |
| supplier_sku.csv | 4626 | `e8308e563483cf6f...` | True | True | True |
| uom_conversion.csv | 6000 | `69f9b453247e6994...` | True | True | True |
