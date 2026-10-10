# Pakistani supermarket demo

This synthetic catalog is not Euro Store data or an image-training dataset.
Products have `[DEMO]` names and SKUs `DEMO-PK-001` through `DEMO-PK-030`.
Four shelves cover Grocery, Dairy, Beverages and Snacks, and Household.
The four associated cameras are disabled with no video sources; their ROIs are
placeholders, not calibrated camera coordinates.

Starting quantities are reproducible and intentionally include adequate, low and
zero stock. Each quantity is entered through the audited manual-correction
service, with history and an outbox event, no camera confidence or observations.
History timestamps represent setup time, not fabricated past sales.

From `backend` with the environment activated:

```powershell
python -m scripts.seed_demo_store --admin-email admin@intellistock.com
python -m scripts.seed_demo_store --admin-email admin@intellistock.com --apply
```

The first command previews only. Applying requires a non-production environment,
disabled email notifications and an active administrator. The insert is atomic;
identifier collisions abort rather than resetting previously edited demo stock.
Existing records, including the earlier `sku110` fixture, are preserved.

## Try the data

- Inventory: search `DEMO-PK`, filter stock states and inspect a product's history.
- Shelves/cameras: inspect the four `DEMO PK` shelves and disabled cameras.
- Reports: filter by a demo shelf and export inventory/history CSV.
- Assistant: ask `Inventory for SKU DEMO-PK-001`, then `Show its history`.
- Manual corrections: change a demo quantity with an explicit test reason and
  inspect the resulting audit/history entry.

Redis and the event worker are required to validate event delivery, alert rules
and real-time updates. Seeding does not fabricate alerts or enable workers.
Camera detection requires actual footage, calibration, mappings and weights.
Email delivery is not part of seeding: before activation review unresolved demo
alerts, since these can be sent to configured recipients too.
