# Find informative projections

A burst table with forty parameters holds 780 two-parameter plots. This panel
(**View ▸ Find informative projections…**, directly below *UMAP*; the
*(z axis)* entry below it ranks the third axis) scores every one of them, in the
background, and lists them best first. **Click
a row and ndX shows that plot.** Choosing axes by hand in the plot selects the
matching row, so you can see where your own choice ranks.

The table fills while it computes. **Pause** stops it and **Start** picks up
where it stopped; closing the panel pauses it too, and reopening resumes. When
it finishes, the best row is selected and shown. The line under the table says
what the selected row's score means, in numbers.

## Rank by

**Separation** (the default) — in which view do the bursts fall into clearly
separated populations? This is the smFRET question: donor-only, acceptor-only
and FRET species pulling apart in E vs S, a dynamic population lying off the
static FRET line in E vs τ or in the variance plot. No labels needed.

The bursts of the view are binned and smoothed; each density peak with a
valley around it is an **island**. A valley counts when it is deeper than the
shot noise of the histogram and the smaller side holds at least 3 % of the
bursts — so a tail or a clump of outliers is not a population. The score is the
**chance that two bursts drawn at random sit in two different, clearly separated
islands**: only the bursts inside an island's core count (not those on a bridge
between two populations, in a tail or in the noise), and a shallow valley counts
for less than empty space. 0 is one population — however elongated, skewed or
correlated it is — 0.5 two equal islands with empty space between them, 0.18 a
10 % island off a 90 % blob, 0.67 three equal islands. The **Islands** column
says how many there are.

Before any pair is scored, the parameters that cannot show molecules apart are
set aside: flags (fewer than 20 values), the acquisition clock (first photon,
macro time), and folds of another parameter (`(1-E)*E` of E). Parameters that
are the same quantity — *Proximity ratio* and *FRET efficiency*, a rate and its
count — are ranked once; the row names the others. Each axis is read the way the
plot draws it (a log axis in decades), with fit sentinels (`-1` where a channel
was not fitted, a bound holding many bursts) and outliers removed and the axis
scaled by its robust range, so a parameter does not win by its units.

**Bursts** — low-photon bursts are wide (shot noise) and fill the valleys
between populations. *Weight by photons* counts each burst by its photons;
*Only bursts with at least Min photons* leaves the dim ones out. Both need a
*Number of Photons* column.

**Show islands on the map** colours the map by the islands found in the view on
the axes (emtk app).

**Use islands as clusters** labels every burst of the table by the island of
the view on the axes and writes the labels as the clusters (`Cluster Label`,
replacing K-means/HDBSCAN clusters) and as a column `Island Label (x vs y)`.
Islands are numbered by the bursts they hold, largest first; a burst on a bridge
between islands, in a thin tail or an outlier gets -1. The Cluster spin box,
*colour*, gates, Save Burst IDs and vector parameters' population axis then
work on the islands.

**Correlation** — which parameters move together (Spearman |ρ|, sign shown)?
It finds related measurements — E and a lifetime, a rate and its count — not
populations; the same set-aside rules apply, so duplicated parameters do not
flood the top.

**Classes** — offered when there are labels: the gate in the Selection table
(inside vs outside), one population per gate, the clusters from *Cluster*, or a
z parameter that holds labels. Do bursts of one class sit next to each other in
this view? For every burst the 10 nearest bursts on screen are found and the
share with the same class is counted, above chance (κ). Parameters a gate is
defined on, and those computed from them, are not ranked against that gate.

## Settings

**Sample** — bursts drawn at random for scoring. The same sample serves every
row, so rows compare like with like. The top of the ranking rarely changes above
a few thousand.

Changing a setting pauses the ranking, and the next **Start** ranks again with
the new settings. Changing the table, the gates or an axis range invalidates the
rows; choosing **View ▸ Find informative projections…** again starts a fresh ranking.

## Further reading

- [Interactive multidimensional exploration](docs/concepts/multidimensional_exploration.md)
- [Exploring & fitting multidimensional data (ndX)](docs/guides/46_ndxplorer.md)
- Edelsbrunner, Letscher & Zomorodian, *Topological persistence and
  simplification* (the elder rule that pairs each density peak with its valley) —
  [10.1007/s00454-002-2885-2](https://doi.org/10.1007/s00454-002-2885-2)
