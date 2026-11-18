# Metabolized methane moonshot TEA

Techno-economic analysis of a methane-reducing cattle implant, on the standard TEA
framework shared with the thermosyphon, prefab-homes and biofuel repos (NOAK costs,
Wright's-law learning, BAU comparison, tornado, Monte Carlo, break-evens, kill
metrics, scorecard).

**The concept.** A slow-release ear implant, in the same form factor and applicator as
beef growth implants, delivers an anti-methanogen antigen for a year. The cow makes
antibodies that reach the rumen in saliva and suppress the archaea that make methane.
The implant carries a passive RFID tag (optionally with temperature) read at the
parlour, chute or trough. The company earns:

- an annual implant fee;
- a data subscription (dairy);
- an aggregator's share of the methane credits or insetting payments the farmer earns.

The two segments are dairy in markets that pay for methane cuts, and grazing beef,
where daily feed additives such as Bovaer cannot reach the animals.

## Run it

```bash
pip install -r requirements.txt
python scripts/run_tea.py methane_implant     # writes results/methane_implant/
python -m pytest
```

## Results (base case)

| Metric | Value |
|---|---|
| NPV (10%, 15 yr) | ~$0 (IRR 10%) |
| P(NPV > 0), Monte Carlo | 23% |
| Peak cash need | $118M |
| Cash breakeven | year 12 |
| Year-15 revenue | $201M (7.5M dairy cows + 10M beef cattle treated) |
| CO2e avoided in year 15 | 8.6 Mt/yr |

**Versus BAU (farmer's cost per t CO2e avoided):**

| Option | $/t CO2e |
|---|---|
| Implant, grazing beef | $12 |
| Implant, dairy | $25 |
| Dairy methane credit / insetting price | $30 |
| Denmark livestock tax, effective 2035 | $43 |
| Bovaer (dairy, fed daily) | $112 |

**What it says**

1. **The technology case is strong.** The implant cuts methane at about a quarter of
   Bovaer's cost per tonne, and it reaches range cattle that feed additives can't.
2. **The business case is thin, because the payer is weak.** A treated dairy cow earns
   the farmer only ~$16/yr in credits at $30/t. That caps the fee at ~$15 and revenue
   at ~$200M, a fifth of the big-enough line.
3. **Beef destroys value at today's prices.** A range animal avoids only 0.39 t/yr,
   worth ~$5. That's about what the dose, channel and verification cost. Dairy alone
   is NPV +$24M; beef alone is −$176M.
4. **The kill metrics are efficacy and duration.** Break-even efficacy is 20% (trials
   so far: 12.9%). A 6-month implant needing two handlings a year drops NPV to −$132M.
5. **What makes it a moonshot is a payer.** At $60/t for dairy and $30/t for beef, NPV
   is +$70M. A Denmark-style tax spreading to other dairy exporters, or a government
   buyer for range-cattle tonnes, is what would scale this.

## Caveats

- The vaccine biology is ArkeaBio's lead; the new parts here are the year-long release
  and the delivery in a growth-implant form factor.
- Passive RFID reads only within about a metre of a reader. Location tracking needs a
  battery-powered collar or bolus, so it is not in this product.
- Cost of goods, prices, adoption and the adverse-event rate are assumptions with ranges.
  Sources are in `inputs/methane_implant.toml`. GWP100 = 27 for methane is from memory.
- Pre-tax, real 2026 USD; no terminal value beyond the 15-year horizon.
