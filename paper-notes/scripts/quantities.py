"""Screen numeric expressions for potential scientific meaning changes."""
import re

NUMBER = r"[+−-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+−-]?\d+)?"
UNIT = r"(?:mmol|mol|ppm|kPa|MPa|Pa|kHz|MHz|Hz|°C|kg|[mµμn]?g|[mµμn]?m|km|[mµμ]?L|ms|s|h|%)"
MEASURE = re.compile(
    r"(?:(?:<=|>=|≤|≥|<|>|≈|~)\s*)?" + NUMBER
    + r"(?:\s*(?:±|–)\s*" + NUMBER + r")?"
    + r"(?:\s*" + UNIT + r"(?:\s*/\s*" + UNIT + r")*(?![A-Za-z]))?"
)

def quantities(text, measured_only=False):
    tokens = []
    for match in MEASURE.finditer(text):
        raw = match.group()
        if measured_only and re.fullmatch(NUMBER, raw):
            continue
        normalized = re.sub(r"\s+", "", raw).replace("−","-").replace("µ","μ")
        tokens.append(normalized.replace("<=","≤").replace(">=","≥"))
    return tokens
