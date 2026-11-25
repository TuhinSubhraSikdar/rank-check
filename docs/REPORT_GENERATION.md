# Report Generation

Implemented Report snapshots are tenant-owned and private. A report freezes
the latest per-configuration observations, summary counts and branding in JSON
at generation time. Owner-only preview and HTML/CSV downloads use that snapshot.
The HTML document embeds CSS without external scripts or stylesheets. CSV cells
neutralize formulas. Date ranges, historical comparison, logo upload and public
sharing are not yet implemented.
