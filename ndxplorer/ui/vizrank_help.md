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

## Scores

**Class separation (k-NN)** — do bursts of one class sit next to each other in
this view? For every burst, the 10 nearest bursts on screen are found and the
share with the same class is counted. The number shown is that share *above
chance* (κ): 0 means no better than the class sizes alone predict, 1 means every
neighbour agrees. When the class is a quantity rather than an id (the z
parameter, say), the score is the R² of predicting it from the neighbours.
Distances are measured the way the plot draws the axes — over each axis' range,
on a log axis in decades — so a parameter does not win by having larger numbers.

The classes can be:

- **the gate** in the Selection table (inside vs outside) — *which other
  parameters distinguish the bursts I gated?*;
- **one population per gate**, when there are several gates (e.g. painted
  mask classes) — bursts in more than one gate are left out;
- **the clusters** from *Cluster* (noise bursts are left out);
- **the z parameter** — what predicts it.

Parameters a gate is defined on are not ranked against that gate: they separate
it by construction, and so do parameters computed from them (E_τ from τ),
which are left out too.

**Population structure (2-means)** — does the view split into more than one
population? No classes needed. The cloud is whitened and split into the two
groups that leave the least spread inside them; the number shown is how much
better that split is than for a single Gaussian cloud. 0 is one population,
about 0.45 is two equal populations four widths apart, 0.7 six widths apart;
negative values are clouds with heavy tails. It looks at the bursts the gates
keep. A split whose smaller group holds under 5 % of the bursts does not count,
and parameters with fewer than 20 distinct values (fit flags) are not scored.

**Correlation (Pearson / Spearman)** — how strongly two parameters co-vary, with
the sign; Spearman uses ranks, so it also finds curved but monotone relations.
Duplicated parameters (a count and its rate over a fixed window) come first —
that is correct, and usually not what you are looking for.

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
- Liu, Hayes, Nobel & Marron, *Statistical significance of clustering for
  high-dimension, low-sample size data* —
  [10.1198/016214508000000454](https://doi.org/10.1198/016214508000000454)
