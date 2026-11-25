# Csv Export

Keyword exports stream ORM rows in chunks and include keyword, target URL,
tags and intent. Report CSV exports include project, keyword, geography,
device, position, movement, ranking URL, checked depth, status, provider and
timestamp from the frozen report snapshot. Both use UTF-8 and neutralize
spreadsheet formula prefixes. Report snapshots currently render CSV in memory;
large historical exports and date range selection remain planned.
