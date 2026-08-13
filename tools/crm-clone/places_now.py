"""All NJ/OH/WV counties for NOW scraping (164 places).

New Jersey: 21 counties
Ohio: 88 counties
West Virginia: 55 counties
"""

from __future__ import annotations

# id (no spaces) -> {name, state, unit: county}
PLACES: dict[str, dict[str, str]] = {}


def _add(state: str, items: list[tuple[str, str]], unit: str) -> None:
    for pid, name in items:
        key = f"{state}:{pid}"
        PLACES[key] = {"id": pid, "name": name, "state": state, "unit": unit}


# --- New Jersey: 21 counties ---
_add(
    "NJ",
    [
        ("Atlantic", "Atlantic"),
        ("Bergen", "Bergen"),
        ("Burlington", "Burlington"),
        ("Camden", "Camden"),
        ("CapeMay", "Cape May"),
        ("Cumberland", "Cumberland"),
        ("Essex", "Essex"),
        ("Gloucester", "Gloucester"),
        ("Hudson", "Hudson"),
        ("Hunterdon", "Hunterdon"),
        ("Mercer", "Mercer"),
        ("Middlesex", "Middlesex"),
        ("Monmouth", "Monmouth"),
        ("Morris", "Morris"),
        ("Ocean", "Ocean"),
        ("Passaic", "Passaic"),
        ("Salem", "Salem"),
        ("Somerset", "Somerset"),
        ("Sussex", "Sussex"),
        ("Union", "Union"),
        ("Warren", "Warren"),
    ],
    "county",
)

# --- Ohio: 88 counties ---
_add(
    "OH",
    [
        ("Adams", "Adams"),
        ("Allen", "Allen"),
        ("Ashland", "Ashland"),
        ("Ashtabula", "Ashtabula"),
        ("Athens", "Athens"),
        ("Auglaize", "Auglaize"),
        ("Belmont", "Belmont"),
        ("Brown", "Brown"),
        ("Butler", "Butler"),
        ("Carroll", "Carroll"),
        ("Champaign", "Champaign"),
        ("Clark", "Clark"),
        ("Clermont", "Clermont"),
        ("Clinton", "Clinton"),
        ("Columbiana", "Columbiana"),
        ("Coshocton", "Coshocton"),
        ("Crawford", "Crawford"),
        ("Cuyahoga", "Cuyahoga"),
        ("Darke", "Darke"),
        ("Defiance", "Defiance"),
        ("Delaware", "Delaware"),
        ("Erie", "Erie"),
        ("Fairfield", "Fairfield"),
        ("Fayette", "Fayette"),
        ("Franklin", "Franklin"),
        ("Fulton", "Fulton"),
        ("Gallia", "Gallia"),
        ("Geauga", "Geauga"),
        ("Greene", "Greene"),
        ("Guernsey", "Guernsey"),
        ("Hamilton", "Hamilton"),
        ("Hancock", "Hancock"),
        ("Hardin", "Hardin"),
        ("Harrison", "Harrison"),
        ("Henry", "Henry"),
        ("Highland", "Highland"),
        ("Hocking", "Hocking"),
        ("Holmes", "Holmes"),
        ("Huron", "Huron"),
        ("Jackson", "Jackson"),
        ("Jefferson", "Jefferson"),
        ("Knox", "Knox"),
        ("Lake", "Lake"),
        ("Lawrence", "Lawrence"),
        ("Licking", "Licking"),
        ("Logan", "Logan"),
        ("Lorain", "Lorain"),
        ("Lucas", "Lucas"),
        ("Madison", "Madison"),
        ("Mahoning", "Mahoning"),
        ("Marion", "Marion"),
        ("Medina", "Medina"),
        ("Meigs", "Meigs"),
        ("Mercer", "Mercer"),
        ("Miami", "Miami"),
        ("Monroe", "Monroe"),
        ("Montgomery", "Montgomery"),
        ("Morgan", "Morgan"),
        ("Morrow", "Morrow"),
        ("Muskingum", "Muskingum"),
        ("Noble", "Noble"),
        ("Ottawa", "Ottawa"),
        ("Paulding", "Paulding"),
        ("Perry", "Perry"),
        ("Pickaway", "Pickaway"),
        ("Pike", "Pike"),
        ("Portage", "Portage"),
        ("Preble", "Preble"),
        ("Putnam", "Putnam"),
        ("Richland", "Richland"),
        ("Ross", "Ross"),
        ("Sandusky", "Sandusky"),
        ("Scioto", "Scioto"),
        ("Seneca", "Seneca"),
        ("Shelby", "Shelby"),
        ("Stark", "Stark"),
        ("Summit", "Summit"),
        ("Trumbull", "Trumbull"),
        ("Tuscarawas", "Tuscarawas"),
        ("Union", "Union"),
        ("VanWert", "Van Wert"),
        ("Vinton", "Vinton"),
        ("Warren", "Warren"),
        ("Washington", "Washington"),
        ("Wayne", "Wayne"),
        ("Williams", "Williams"),
        ("Wood", "Wood"),
        ("Wyandot", "Wyandot"),
    ],
    "county",
)

# --- West Virginia: 55 counties ---
_add(
    "WV",
    [
        ("Barbour", "Barbour"),
        ("Berkeley", "Berkeley"),
        ("Boone", "Boone"),
        ("Braxton", "Braxton"),
        ("Brooke", "Brooke"),
        ("Cabell", "Cabell"),
        ("Calhoun", "Calhoun"),
        ("Clay", "Clay"),
        ("Doddridge", "Doddridge"),
        ("Fayette", "Fayette"),
        ("Gilmer", "Gilmer"),
        ("Grant", "Grant"),
        ("Greenbrier", "Greenbrier"),
        ("Hampshire", "Hampshire"),
        ("Hancock", "Hancock"),
        ("Hardy", "Hardy"),
        ("Harrison", "Harrison"),
        ("Jackson", "Jackson"),
        ("Jefferson", "Jefferson"),
        ("Kanawha", "Kanawha"),
        ("Lewis", "Lewis"),
        ("Lincoln", "Lincoln"),
        ("Logan", "Logan"),
        ("Marion", "Marion"),
        ("Marshall", "Marshall"),
        ("Mason", "Mason"),
        ("McDowell", "McDowell"),
        ("Mercer", "Mercer"),
        ("Mineral", "Mineral"),
        ("Mingo", "Mingo"),
        ("Monongalia", "Monongalia"),
        ("Monroe", "Monroe"),
        ("Morgan", "Morgan"),
        ("Nicholas", "Nicholas"),
        ("Ohio", "Ohio"),
        ("Pendleton", "Pendleton"),
        ("Pleasants", "Pleasants"),
        ("Pocahontas", "Pocahontas"),
        ("Preston", "Preston"),
        ("Putnam", "Putnam"),
        ("Raleigh", "Raleigh"),
        ("Randolph", "Randolph"),
        ("Ritchie", "Ritchie"),
        ("Roane", "Roane"),
        ("Summers", "Summers"),
        ("Taylor", "Taylor"),
        ("Tucker", "Tucker"),
        ("Tyler", "Tyler"),
        ("Upshur", "Upshur"),
        ("Wayne", "Wayne"),
        ("Webster", "Webster"),
        ("Wetzel", "Wetzel"),
        ("Wirt", "Wirt"),
        ("Wood", "Wood"),
        ("Wyoming", "Wyoming"),
    ],
    "county",
)

assert len([k for k in PLACES if k.startswith("NJ:")]) == 21
assert len([k for k in PLACES if k.startswith("OH:")]) == 88
assert len([k for k in PLACES if k.startswith("WV:")]) == 55
assert len(PLACES) == 164

PRIORITY = [
    "NJ:Bergen",
    "NJ:Essex",
    "NJ:Hudson",
    "NJ:Middlesex",
    "NJ:Monmouth",
    "NJ:Ocean",
    "NJ:Union",
    "NJ:Passaic",
    "NJ:Camden",
    "NJ:Mercer",
    "NJ:Morris",
    "NJ:Burlington",
    "OH:Cuyahoga",
    "OH:Franklin",
    "OH:Hamilton",
    "OH:Summit",
    "OH:Montgomery",
    "OH:Lucas",
    "OH:Stark",
    "OH:Butler",
    "OH:Lorain",
    "OH:Mahoning",
    "OH:Lake",
    "OH:Warren",
    "OH:Clermont",
    "OH:Delaware",
    "OH:Medina",
    "WV:Kanawha",
    "WV:Berkeley",
    "WV:Monongalia",
    "WV:Cabell",
    "WV:Wood",
    "WV:Raleigh",
    "WV:Harrison",
    "WV:Jefferson",
    "WV:Putnam",
    "WV:Marion",
]

QUERY_TEMPLATES = {
    "county": [
        "real estate developer {name} County {st}",
        "land developer {name} County {st}",
        "home builder {name} County {st}",
    ],
}

_ALIASES = {
    "capemay": "CapeMay",
    "vanwert": "VanWert",
}


def _norm_tok(s: str) -> str:
    return s.replace(" ", "").replace("_", "").replace("-", "").replace(".", "")


def canonical_id(key: str) -> str:
    k = key.strip()
    if ":" in k:
        st, rest = k.split(":", 1)
        st = st.upper()
        rest = _norm_tok(rest)
        if rest.lower() in _ALIASES:
            rest = _ALIASES[rest.lower()]
        cand = f"{st}:{rest}"
        if cand in PLACES:
            return cand
        lower = {p.split(":", 1)[1].lower(): p for p in PLACES if p.startswith(f"{st}:")}
        if rest.lower() in lower:
            return lower[rest.lower()]
        raise KeyError(f"Unknown place id: {key}")

    tok = _norm_tok(k)
    if tok.lower() in _ALIASES:
        tok = _ALIASES[tok.lower()]
    hits = [p for p in PLACES if p.split(":", 1)[1].lower() == tok.lower()]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        raise KeyError(f"Ambiguous place '{key}' — use ST:Name (candidates: {hits})")
    raise KeyError(f"Unknown place id: {key}")


def resolve(key: str) -> dict[str, str]:
    return PLACES[canonical_id(key)]


def queries_for(place_id: str) -> list[str]:
    meta = resolve(place_id)
    unit = meta["unit"]
    name = meta["name"]
    st = meta["state"]
    return [tmpl.format(name=name, st=st) for tmpl in QUERY_TEMPLATES[unit]]


def remaining(
    done_ids: set[str],
    states: set[str] | None = None,
) -> list[str]:
    done: set[str] = set()
    for d in done_ids:
        try:
            done.add(canonical_id(d))
        except KeyError:
            if d in PLACES:
                done.add(d)

    state_order = ("NJ", "OH", "WV")
    if states:
        want = {s.upper() for s in states}
        state_order = tuple(s for s in state_order if s in want)
    ordered: list[str] = []
    seen: set[str] = set()

    for st in state_order:
        pri = [p for p in PRIORITY if p.startswith(f"{st}:")]
        rest = sorted(p for p in PLACES if p.startswith(f"{st}:") and p not in pri)
        for p in pri + rest:
            if p in seen:
                continue
            seen.add(p)
            if p not in done:
                ordered.append(p)
    return ordered


def place_file_slug(place_id: str) -> str:
    return canonical_id(place_id).replace(":", "_")


if __name__ == "__main__":
    print(f"places={len(PLACES)} remaining_all={len(remaining(set()))}")
    for st in ("NJ", "OH", "WV"):
        print(f"  {st}={sum(1 for p in PLACES if p.startswith(f'{st}:'))}")
    print("next:", remaining(set())[:8])
