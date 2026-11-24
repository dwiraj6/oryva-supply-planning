"""Scale presets and business parameters.

Every number the generator or planner uses lives here so behaviour is
documented in one place and starter/full runs share identical logic.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

DEFAULT_SEED = 20261022
SNAPSHOT_WEEK = 1          # plan is run as of the start of 2026W01
HORIZON_WEEKS = 52         # 2026W01 .. 2026W52


@dataclass(frozen=True)
class Scale:
    name: str
    n_skus: int
    n_locations: int
    n_weeks: int
    n_suppliers: int
    n_pos: int                 # baseline inbound purchase orders
    edge_cases_per_type: int   # injected anomalies per issue type
    boundary_per_type: int     # valid boundary records per boundary type
    compress: bool             # gzip the large CSV exports

    def to_dict(self) -> dict:
        return asdict(self)


SCALES: dict[str, Scale] = {
    "starter": Scale("starter", 100, 5, 52, 20, 300, 5, 3, False),
    "full": Scale("full", 3000, 50, 52, 500, 10000, 40, 10, True),
}

CATEGORIES = [
    "BEVERAGES", "SNACKS", "DAIRY", "HOUSEHOLD",
    "PERSONAL_CARE", "ELECTRONICS", "HARDWARE", "PHARMA",
]
REGIONS = ["NORTH", "SOUTH", "EAST", "WEST", "CENTRAL"]
CARRIERS = {  # carrier -> on-time reliability
    "BLUEDART_FREIGHT": 0.93, "RAILCO": 0.85, "SEALINK": 0.78,
    "ROADSTAR": 0.88, "AIRFAST": 0.96, "CONTAINERX": 0.80,
}
PACK_SIZES = [6, 12, 24, 48]

P = {
    # --- master data mix
    "abc_split": (0.20, 0.30, 0.50),          # A, B, C share of SKUs
    "make_share": 0.15,                       # SKUs manufactured in-house
    "plant_every_n_locations": 10,            # LOC-001, LOC-011, ... are plants
    "dc_share_of_non_plants": 0.65,
    "supplier_on_hold_share": 0.05,
    "supplier_tight_share": 0.12,             # latent tightness; flag is derived
    "substitute_share": 0.20,                 # SKUs that have a substitute
    "substitute_approved_share": 0.70,
    # --- demand
    "level_median": {"A": 120.0, "B": 40.0, "C": 8.0},   # units / week / location
    "level_sigma": 0.6,
    "location_weight_sigma": 0.35,
    "nb_dispersion": 4.0,
    "spike_rate": 0.03,
    "spike_multiplier": (1.0, 4.0),
    "c_occurrence": (0.35, 0.80),
    # --- assortment (#locations per SKU)
    "locations_per_sku": {"A": (4, 10), "B": (2, 6), "C": (1, 3)},
    # --- inventory cover (weeks of mean demand); slow C movers are typically overstocked
    "cover_weeks": {"A": (3, 8), "B": (4, 12), "C": (20, 60), "MAKE": (1, 3), "COMPONENT": (2, 6)},
    "allocated_share": (0.0, 0.08),
    "safety_stock_weeks": {"A": 2.0, "B": 1.5, "C": 1.0},
    # --- purchase orders
    "po_cover_weeks": (6, 14),
    "primary_supplier_prob": 0.75,
    "cancel_rate": 0.02,
    "unconfirmed_rate": 0.05,
    "substitute_po_rate": 0.015,
    "case_uom_share": 0.70,
    # --- planning / mitigation policy
    "transfer_lead_weeks": 1,
    "production_lead_weeks": 1,
    "order_fixed_cost": 150.0,
    "transfer_fixed_cost": 200.0,
    "transfer_unit_cost_rate": 0.04,
    "substitute_fixed_cost": 100.0,
    "produce_fixed_cost": 300.0,
    "produce_unit_cost_rate": 0.08,
    "expedite_fixed_cost": 500.0,
    "expedite_unit_cost_rate": 0.25,
    "abc_weight": {"A": 3.0, "B": 2.0, "C": 1.0},
    "ops_approval_threshold": 5000.0,          # selected spend needing operations-manager approval
    "urgency_halflife_weeks": 4.0,
}
