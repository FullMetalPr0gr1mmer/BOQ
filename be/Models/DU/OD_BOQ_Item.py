"""
OD BOQ Item Model - SQLAlchemy model for BOQ items with multi-level header structure

This model represents the BOQ items with:
- Fixed columns: CAT, BU, Category, Description, UoM
- Quantity columns for each scope type (20 scope columns)
- Total quantity column
- Reference to DU Project

The CSV has a complex header structure:
- Row 1: Level 1 headers (main categories like "New SRAN", "SRAN Expansion", "5G Expansion", etc.)
- Row 4: Level 2 headers (actual column descriptions with OD_SRAN, OD_5G codes)
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text
from Database.session import Base


class ODBOQItem(Base):
    """BOQ Item with quantities for different scope types"""
    __tablename__ = 'du_od_boq_item'

    id = Column(Integer, primary_key=True, index=True)

    # Fixed metadata columns
    cat = Column(String(50), index=True, nullable=True)  # CAT (e.g., "OD")
    bu = Column(String(100), index=True, nullable=True)  # BU (e.g., "Product", "Services")
    category = Column(String(100), index=True, nullable=True)  # Cat. (e.g., "HW", "SW", "Service")
    description = Column(Text, nullable=True)  # Description (e.g., "AMIx AirScale Ultra High Capacity...")
    uom = Column(String(50), nullable=True)  # UoM (e.g., "each", "per cell", "per Sector")

    # Scope Type 1: New SRAN (new 3g/lte as per scope)
    # OD_SRAN 3 Sectors 2xU900+1xLTE800+1xLTE1800+1xL2100 New Sites 3G/LTE 3CC
    new_sran = Column(Float, nullable=True)

    # Scope Type 2: SRAN Expansion - 1cc to 3cc (L800)
    # OD_SRAN HW+SW Expansion 3 Sectors 1cc (l800) to 3cc (800/1800/2100) expansion
    sran_exp_1cc_l800 = Column(Float, nullable=True)

    # Scope Type 3: SRAN Expansion - 1cc to 3cc (L1800)
    # OD_SRAN HW+SW Expansion 3 Sectors 1cc (l1800) to 3cc (800/1800/2100) expansion
    sran_exp_1cc_l1800 = Column(Float, nullable=True)

    # Scope Type 4: SRAN Expansion - 2cc to 3cc (L800+L1800)
    # OD_SRAN HW+SW Expansion 3 Sectors 2cc (l800+l1800) to 3cc (800/1800/2100)
    sran_exp_2cc_l800_l1800 = Column(Float, nullable=True)

    # Scope Type 5: SRAN Expansion - 2cc to 3cc (L1800+L2100)
    # OD_SRAN HW+SW Expansion 3 Sectors 2cc (l1800+l2100) to 3cc (800/1800/2100)
    sran_exp_2cc_l1800_l2100 = Column(Float, nullable=True)

    # Scope Type 6: SRAN Expansion - 2cc to 3cc (L800+L2100) SW only
    # OD_SRAN SW Expansion 3 Sectors 2cc (l800+l2100) to 3cc (800/1800/2100)
    sran_exp_2cc_l800_l2100 = Column(Float, nullable=True)

    # Scope Type 7: New 5G-n78 (new colocation n78)
    # OD_5G 3 Sectors 2CC 64T64R-200M-320W 2x5G NR N78 (New)
    new_5g_n78 = Column(Float, nullable=True)

    # Scope Type 8: 5G Expansion-3CC (new colocation 3cc)
    # OD_5G 3 Sectors 3CC 64T64R_300M-320W 2x5G NR N78 (New) + 1x5G NR N41 (Re-Use HW)
    exp_5g_3cc = Column(Float, nullable=True)

    # Scope Type 9: 5G Expansion-n41 Re-use (new colocation n41 re-deployment)
    # OD_5G 3 Sectors 1CC n41 Redeployment with Service (Redeploy AAU)
    exp_5g_n41_reuse = Column(Float, nullable=True)

    # Scope Type 10: 5G Expansion-3CC (ontop of existing n41)
    # OD_5G 3 Sectors 3CC 64T64R_200M-320W 2x5G NR N78 GHz ontop of existing n41
    exp_5g_3cc_ontop = Column(Float, nullable=True)

    # Scope Type 11: 5G Expansion-Band Swap (n41 to n78)
    # OD_5G 3 Sectors 2CC 64T64R-200M-320W 2x5G NR N78 (BandSwap) n41 (Dismantle HW) to n78
    exp_5g_band_swap = Column(Float, nullable=True)

    # Scope Type 12: 5G-NR FDD-Model 1 (5g fdd n3 activation)
    # OD_5G 3 Sectors 2T2R_15MHz FDD NR_1800MHz (HW &or SW) Together With BandSWAP
    nr_fdd_model1_activation = Column(Float, nullable=True)

    # Scope Type 13: 5G-NR FDD-Model 1 (5g fdd n3 readiness - TDRA Scope)
    # OD_5G 5g fdd n3 readiness only if 1800 RF Mod exist - ABIP
    nr_fdd_model1_tdra = Column(Float, nullable=True)

    # Scope Type 14: 5G-NR FDD-Model 1 (5g fdd n3 readiness - 2025 Scope, Not TDRA)
    # OD_5G 5g fdd n3 readiness for the 2025 Scope Sites (Not TDRA)
    nr_fdd_model1_2025 = Column(Float, nullable=True)

    # Scope Type 15: Antenna Cutover (IPAA+)
    # IPAA & Services
    antenna_cutover_ipaa = Column(Float, nullable=True)

    # Total Quantity column
    total_qty = Column(Float, nullable=True)

    # Foreign key to DU Project
    project_id = Column(String(200), ForeignKey("du_project.pid_po"), index=True, nullable=True)

    # Note: Header metadata is stored in LEVEL1_CATEGORIES and LEVEL2_DESCRIPTIONS constants
    # Use the /boq-items/column-headers endpoint to get header mappings for display


# Column mapping for CSV import
# Maps column index to model field name
CSV_COLUMN_MAPPING = {
    0: 'cat',           # CAT
    1: 'bu',            # BU
    2: 'category',      # Cat.
    3: 'description',   # Description
    4: 'uom',           # UoM
    5: 'new_sran',      # New SRAN
    6: 'sran_exp_1cc_l800',       # SRAN Expansion 1cc to 3cc (L800)
    7: 'sran_exp_1cc_l1800',      # SRAN Expansion 1cc to 3cc (L1800)
    8: 'sran_exp_2cc_l800_l1800', # SRAN Expansion 2cc to 3cc (L800+L1800)
    9: 'sran_exp_2cc_l1800_l2100',# SRAN Expansion 2cc to 3cc (L1800+L2100)
    10: 'sran_exp_2cc_l800_l2100',# SRAN Expansion 2cc to 3cc (L800+L2100)
    11: 'new_5g_n78',             # New 5G-n78
    12: 'exp_5g_3cc',             # 5G Expansion-3CC
    13: 'exp_5g_n41_reuse',       # 5G Expansion-n41 Re-use
    14: 'exp_5g_3cc_ontop',       # 5G Expansion-3CC (ontop)
    15: 'exp_5g_band_swap',       # 5G Expansion-Band Swap
    16: 'nr_fdd_model1_activation',# 5G-NR FDD-Model 1 (activation)
    17: 'nr_fdd_model1_tdra',     # 5G-NR FDD-Model 1 (TDRA)
    18: 'nr_fdd_model1_2025',     # 5G-NR FDD-Model 1 (2025)
    19: 'antenna_cutover_ipaa',   # Antenna Cutover (IPAA+)
    20: 'total_qty',              # Total Qty
}

# Reverse mapping (field name to column index)
FIELD_TO_COLUMN = {v: k for k, v in CSV_COLUMN_MAPPING.items()}

# Level 1 header categories (from row 1 of CSV)
LEVEL1_CATEGORIES = {
    'new_sran': 'New SRAN',
    'sran_exp_1cc_l800': '1cc to 3cc (L800)',
    'sran_exp_1cc_l1800': '1cc to 3cc (L1800)',
    'sran_exp_2cc_l800_l1800': '2cc to 3cc (L800+L1800)',
    'sran_exp_2cc_l1800_l2100': '2cc to 3cc (L1800+L2100)',
    'sran_exp_2cc_l800_l2100': '2cc to 3cc (L800+L2100)',
    'new_5g_n78': 'New 5G -n78',
    'exp_5g_3cc': '5G Expansion-3CC',
    'exp_5g_n41_reuse': '5G Expansion-n41 Re-use',
    'exp_5g_3cc_ontop': '5G Expansion-3CC',
    'exp_5g_band_swap': '5G Expansion-Band Swap',
    'nr_fdd_model1_activation': '5G-NR FDD-Model 1',
    'nr_fdd_model1_tdra': '5G-NR FDD-Model 1',
    'nr_fdd_model1_2025': '5G-NR FDD-Model 1',
    'antenna_cutover_ipaa': 'Antenna Cutover (IPAA+)',
}

# Level 2 header descriptions (from row 4)
LEVEL2_DESCRIPTIONS = {
    'new_sran': 'OD_SRAN 3 Sectors 2xU900+1xLTE800+1xLTE1800+1xL2100 New Sites 3G/LTE 3CC',
    'sran_exp_1cc_l800': 'OD_SRAN HW+SW Expansion 3 Sectors 1cc (l800) to 3cc',
    'sran_exp_1cc_l1800': 'OD_SRAN HW+SW Expansion 3 Sectors 1cc (l1800) to 3cc',
    'sran_exp_2cc_l800_l1800': 'OD_SRAN HW+SW Expansion 3 Sectors 2cc (l800+l1800) to 3cc',
    'sran_exp_2cc_l1800_l2100': 'OD_SRAN HW+SW Expansion 3 Sectors 2cc (l1800+l2100) to 3cc',
    'sran_exp_2cc_l800_l2100': 'OD_SRAN SW Expansion 3 Sectors 2cc (l800+l2100) to 3cc',
    'new_5g_n78': 'OD_5G 3 Sectors 2CC 64T64R-200M-320W 2x5G NR N78 (New)',
    'exp_5g_3cc': 'OD_5G 3 Sectors 3CC 64T64R_300M-320W 2x5G NR N78 + N41',
    'exp_5g_n41_reuse': 'OD_5G 3 Sectors 1CC n41 Redeployment',
    'exp_5g_3cc_ontop': 'OD_5G 3 Sectors 3CC 64T64R_200M-320W ontop existing n41',
    'exp_5g_band_swap': 'OD_5G 3 Sectors 2CC BandSwap n41 to n78',
    'nr_fdd_model1_activation': 'OD_5G 3 Sectors FDD NR_1800MHz activation',
    'nr_fdd_model1_tdra': 'OD_5G 5g fdd n3 readiness TDRA Scope',
    'nr_fdd_model1_2025': 'OD_5G 5g fdd n3 readiness 2025 Scope',
    'antenna_cutover_ipaa': 'IPAA & Services',
}

# Quantity column fields (all numeric columns)
QUANTITY_FIELDS = [
    'new_sran',
    'sran_exp_1cc_l800',
    'sran_exp_1cc_l1800',
    'sran_exp_2cc_l800_l1800',
    'sran_exp_2cc_l1800_l2100',
    'sran_exp_2cc_l800_l2100',
    'new_5g_n78',
    'exp_5g_3cc',
    'exp_5g_n41_reuse',
    'exp_5g_3cc_ontop',
    'exp_5g_band_swap',
    'nr_fdd_model1_activation',
    'nr_fdd_model1_tdra',
    'nr_fdd_model1_2025',
    'antenna_cutover_ipaa',
    'total_qty',
]
