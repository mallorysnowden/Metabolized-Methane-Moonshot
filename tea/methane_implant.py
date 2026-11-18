"""Methane-reducing cattle implant: TEA on the standard framework.

A slow-release ear implant (the same form factor and applicator as beef growth implants)
delivers an anti-methanogen antigen for a year. The cow makes antibodies that reach the
rumen in saliva and suppress the archaea that make methane. The implant also carries a
passive RFID tag, optionally with a temperature sensor, read at the parlour, chute or
water trough.

Revenue per treated head: an annual implant fee, an optional data subscription (dairy),
and an aggregator's share of the methane credits or insetting payments the farmer earns.
Two segments: dairy in markets that pay for methane cuts, and grazing beef, where daily
feed additives such as Bovaer cannot reach the animals.
"""
from __future__ import annotations

from .finance import irr, npv
from .framework.learning import cost_multiplier
from .framework.result import FunctionalUnit, KillMetric, StandardResult, YearRow

SEGMENTS = ("dairy", "beef")


def avoided_t(v, seg: str) -> float:
    """t CO2e avoided per treated head-year."""
    return v[f"{seg}.ch4_kg"] / 1000 * v["ghg.gwp100_ch4"] * v["implant.efficacy"]


def doses_per_year(v) -> float:
    return 12 / v["implant.duration_months"]


def farmer_value(v, seg: str) -> dict:
    """What one treated head-year is worth to the farmer, before paying for the implant."""
    credits = avoided_t(v, seg) * v[f"{seg}.carbon_value"] * (1 - v["company.aggregator_share"])
    productivity = v[f"{seg}.output_value"] * v["implant.productivity_gain"]
    data = v["data.farmer_value"] * v["data.enabled"] if seg == "dairy" else 0.0
    return {"credits": credits, "productivity": productivity, "data": data}


def farmer_cost(v, seg: str) -> float:
    fee = v[f"{seg}.price"] + (v["data.fee"] * v["data.enabled"] if seg == "dairy" else 0.0)
    return fee + v["implant.admin_cost"] * doses_per_year(v)


def farmer_net(v, seg: str) -> float:
    return sum(farmer_value(v, seg).values()) - farmer_cost(v, seg)


def cost_per_t(v, seg: str) -> float:
    """Farmer's cost per t CO2e avoided (implant fee and handling only)."""
    avoided = avoided_t(v, seg)
    return (v[f"{seg}.price"] + v["implant.admin_cost"] * doses_per_year(v)) / avoided if avoided else float("inf")


def bovaer_cost_per_t(v) -> float:
    avoided = v["dairy.ch4_kg"] / 1000 * v["ghg.gwp100_ch4"] * v["bau.bovaer_efficacy"]
    return v["bau.bovaer_cost"] / avoided


def share(v, seg: str, k: int) -> float:
    """Share of the segment's addressable head treated in commercial year k."""
    if k < 1:
        return 0.0
    return v[f"{seg}.max_share"] * min(1.0, k / v[f"{seg}.ramp_years"])


def functional_units(v) -> list[FunctionalUnit]:
    dk43 = v["bau.denmark_tax_2035"]
    fu_t = FunctionalUnit(
        "Farmer's cost per t CO2e avoided", "$/t CO2e",
        {"Implant, dairy": cost_per_t(v, "dairy"), "Implant, grazing beef": cost_per_t(v, "beef"),
         "Bovaer (dairy, fed daily)": bovaer_cost_per_t(v),
         "Denmark livestock tax, effective 2035 (cost of doing nothing)": dk43,
         "Dairy methane credit / insetting price": v["dairy.carbon_value"]},
        "Bovaer and other daily feed additives cannot reach animals on open range.",
    )
    bov_avoided = v["dairy.ch4_kg"] / 1000 * v["ghg.gwp100_ch4"] * v["bau.bovaer_efficacy"]
    fu_net = FunctionalUnit(
        "Dairy farmer's net gain per cow-year (credits + data + productivity - cost)", "$/cow-yr",
        {"Implant": farmer_net(v, "dairy"),
         "Bovaer with credits": bov_avoided * v["dairy.carbon_value"] - v["bau.bovaer_cost"],
         "Health bolus (smaXtec-type), data only": v["bau.bolus_value"] - v["bau.bolus_cost"]},
        "Positive = farmer comes out ahead. The bolus row is a data-only benchmark with no methane benefit.",
    )
    return [fu_t, fu_net]


def run(v) -> StandardResult:
    horizon = int(v["finance.horizon"])
    rd = int(round(v["company.rd_years"]))
    rate = v["finance.company_discount_rate"]
    exp = v["learning.first_year_experience"]
    noak_exp = v["learning.noak_experience"]
    lr = v["learning.rate_cogs"]
    dpy = doses_per_year(v)

    rows: list[YearRow] = []
    cumulative = learning_investment = 0.0
    capacity = 0.0
    noak_year = None
    for t in range(1, horizon + 1):
        k = t - rd
        streams = {"implants": 0.0, "data": 0.0, "credit_share": 0.0}
        heads = {s: v[f"{s}.addressable_head"] * share(v, s, k) for s in SEGMENTS}
        doses = sum(heads.values()) * dpy
        mult = cost_multiplier(max(exp, 1.0), noak_exp, 1.0, lr)
        for s in SEGMENTS:
            streams["implants"] += heads[s] * v[f"{s}.price"]
            streams["credit_share"] += heads[s] * avoided_t(v, s) * v[f"{s}.carbon_value"] * v["company.aggregator_share"]
        streams["data"] = heads["dairy"] * v["data.attach"] * v["data.fee"] * v["data.enabled"]
        cogs = doses * v["implant.cogs"] * mult
        learning_investment += doses * v["implant.cogs"] * (mult - 1)
        cos = (cogs + streams["implants"] * v["company.channel_margin"]
               + sum(heads.values()) * v["company.mrv_cost"]
               + streams["data"] * (1 - v["data.margin"]))
        revenue = sum(streams.values())
        phase = "R&D" if k < 1 else "commercial"
        overhead = v["company.rd_opex"] if phase == "R&D" else v["company.corporate_opex"] + revenue * v["company.sales_share"]
        capex = max(doses - capacity, 0.0) * v["implant.capex_per_dose"]
        capacity = max(capacity, doses)
        gross = revenue - cos
        ebit = gross - overhead
        cumulative += ebit - capex
        rows.append(YearRow(t, phase, revenue, cos, gross, overhead, ebit, cumulative, mult, streams, capex))
        exp += doses
        if noak_year is None and exp >= noak_exp:
            noak_year = t

    cash = [r.ebit - r.capex for r in rows]
    went_negative, breakeven_year = False, None
    for r in rows:
        if r.cumulative_cash < 0:
            went_negative = True
        elif went_negative and breakeven_year is None:
            breakeven_year = r.year

    big = v["scale.big_enough_revenue"]
    eff, dur = v["implant.efficacy"], v["implant.duration_months"]
    ae = v["implant.adverse_event_rate"]
    kills = [
        KillMetric("Methane cut sustained over the implant's life", eff, 0.15, "fraction (>=0.15)", eff >= 0.15,
                   "ArkeaBio's prototype vaccine cut methane 12.9% over 105 days"),
        KillMetric("Implant duration", dur, 12, "months (>=12)", dur >= 12,
                   "One implant per year at routine handling; shorter means extra handling on range cattle"),
        KillMetric("Farmer cost per t CO2e avoided, grazing beef", cost_per_t(v, "beef"), 50, "$/t (<=50)",
                   cost_per_t(v, "beef") <= 50, "Your kill metric; $50/t is a judgment, near Denmark's 2035 effective tax"),
        KillMetric("Farmer net gain, dairy", farmer_net(v, "dairy"), 0, "$/cow-yr (>=0)", farmer_net(v, "dairy") >= 0),
        KillMetric("Farmer net gain, grazing beef", farmer_net(v, "beef"), 0, "$/head-yr (>=0)", farmer_net(v, "beef") >= 0),
        KillMetric("Serious adverse events per implanted head", ae, 0.001, "rate (<=0.001)", ae <= 0.001,
                   "Target to prove in trials; Denmark's Bovaer rollout shows how fast welfare reports stall adoption"),
        KillMetric("Revenue at full scale vs big-enough line", rows[-1].revenue / big, 1.0, "x", rows[-1].revenue >= big),
    ]
    heads_15 = {s: v[f"{s}.addressable_head"] * share(v, s, horizon - rd) for s in SEGMENTS}
    abated = sum(heads_15[s] * avoided_t(v, s) for s in SEGMENTS)
    seg_table = ("Per-head economics by segment", ["Item", "Dairy", "Grazing beef"], [
        ["Enteric CH4 (kg/head-yr)", f"{v['dairy.ch4_kg']:.0f}", f"{v['beef.ch4_kg']:.0f}"],
        ["CO2e avoided (t/head-yr)", f"{avoided_t(v, 'dairy'):.2f}", f"{avoided_t(v, 'beef'):.2f}"],
        ["Credit value to farmer ($/head-yr)", f"${farmer_value(v, 'dairy')['credits']:.2f}", f"${farmer_value(v, 'beef')['credits']:.2f}"],
        ["Implant fee ($/head-yr)", f"${v['dairy.price']:.2f}", f"${v['beef.price']:.2f}"],
        ["Farmer net gain ($/head-yr)", f"${farmer_net(v, 'dairy'):.2f}", f"${farmer_net(v, 'beef'):.2f}"],
        ["Head treated in final year (M)", f"{heads_15['dairy'] / 1e6:.1f}", f"{heads_15['beef'] / 1e6:.1f}"],
    ])
    return StandardResult(
        project="Methane-reducing cattle implant",
        years=rows,
        npv=npv(rate, cash),
        irr=irr(cash),
        peak_cash_need=-min(0.0, min(r.cumulative_cash for r in rows)),
        breakeven_year=breakeven_year,
        full_scale_revenue=rows[-1].revenue,
        functional_units=functional_units(v),
        learning={"implant cost of goods": (cost_multiplier(v["learning.first_year_experience"], noak_exp, 1.0, lr), 1.0)},
        noak_year=noak_year,
        learning_investment=learning_investment,
        kill_metrics=kills,
        tables=[seg_table],
        notes=[
            f"Impact check: {abated / 1e6:,.1f} Mt CO2e/yr avoided in the final year, against ~3 Gt/yr from livestock.",
            "Passive RFID gives ID (and temperature, with a sensor tag) only within about a metre of a reader. "
            "Location tracking needs a battery-powered collar or bolus, so it is not in this product.",
            "Cost of goods learns with cumulative doses made (Wright's law); multipliers are relative to NOAK cost.",
            f"CH4 converted at GWP100 = {v['ghg.gwp100_ch4']:.0f}.",
        ],
    )


def breakevens(v) -> list[dict]:
    from .framework.uncertainty import breakeven
    npv_of = lambda x: run(x).npv  # noqa: E731
    items = [
        ("implant.efficacy", 0.01, 0.8, "Methane cut for NPV = 0"),
        ("dairy.carbon_value", 0, 300, "Dairy credit price ($/t) for NPV = 0"),
        ("implant.cogs", 0, 50, "NOAK cost per dose for NPV = 0"),
        ("dairy.price", 0, 100, "Dairy implant fee for NPV = 0"),
    ]
    return [{"question": q, "input": key, "answer": breakeven(v, key, npv_of, 0.0, lo, hi), "base": v[key]}
            for key, lo, hi, q in items]


def scenarios(v) -> list[tuple[str, dict]]:
    return [
        ("Trial-level efficacy (13%)", {"implant.efficacy": 0.13}),
        ("Bovaer-level efficacy (30%)", {"implant.efficacy": 0.30}),
        ("6-month implant (two handlings a year)", {"implant.duration_months": 6}),
        ("Dairy only", {"beef.max_share": 0.0}),
        ("Beef only", {"dairy.max_share": 0.0}),
        ("No data subscription", {"data.enabled": 0}),
        ("Credits at $60/t (dairy) and $30/t (beef)", {"dairy.carbon_value": 60, "beef.carbon_value": 30}),
        ("1% productivity gain from saved feed energy", {"implant.productivity_gain": 0.01}),
    ]
