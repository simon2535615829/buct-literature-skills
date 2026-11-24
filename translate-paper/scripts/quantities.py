"""Conservative normalization for scientific measurements and comparison signs."""
import re
from decimal import Decimal

NUMBER = r"[+−-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+−-]?\d+)?"
UNIT = r"(?:mmol|mol|ppm|kPa|MPa|Pa|kHz|MHz|Hz|°C|kg|[mµμn]?g|km|cm|[mµμn]?m|[mµμ]?L|min|[mµμn]?s|h|%)"
MEASURE = re.compile(
    r"(?P<sign><=|>=|≤|≥|<|>|≈|~)?\s*(?P<value>" + NUMBER + r")"
    + r"(?:\s*(?P<join>±|–)\s*(?P<other>" + NUMBER + r"))?"
    + r"(?:\s*(?P<unit>" + UNIT + r"(?:\s*/\s*" + UNIT + r")*)(?![A-Za-z]))?"
)
UNITS = {}
for dimension, factors in {
    "mass": {"kg":"1000","g":"1","mg":"1e-3","μg":"1e-6","ng":"1e-9"},
    "length": {"km":"1000","m":"1","cm":"1e-2","mm":"1e-3","μm":"1e-6","nm":"1e-9"},
    "time": {"h":"3600","min":"60","s":"1","ms":"1e-3","μs":"1e-6","ns":"1e-9"},
    "frequency": {"MHz":"1e6","kHz":"1e3","Hz":"1"},
    "pressure": {"MPa":"1e6","kPa":"1000","Pa":"1"},
    "volume": {"L":"1","mL":"1e-3","μL":"1e-6"},
    "amount": {"mol":"1","mmol":"1e-3"},
}.items():
    for unit, factor in factors.items():
        UNITS[unit] = dimension, Decimal(factor)


def quantities(text, measured_only=False):
    tokens = []
    for m in MEASURE.finditer(text):
        raw = (m["unit"] or "").replace("µ", "μ")
        if measured_only and not any((raw, m["sign"], m["join"])):
            continue
        parts = [part.strip() for part in raw.split("/")]
        dims, factor = [], Decimal(1)
        for index, unit in enumerate(parts):
            dim, scale = UNITS.get(unit, (unit, Decimal(1)))
            dims.append(dim)
            factor = factor / scale if index else scale
        values = tuple(Decimal(v.replace("−","-")) * factor for v in (m["value"], m["other"]) if v)
        sign = {"<=":"≤",">=":"≥"}.get(m["sign"], m["sign"])
        tokens.append((sign, m["join"], tuple(dims), values))
    return tokens
