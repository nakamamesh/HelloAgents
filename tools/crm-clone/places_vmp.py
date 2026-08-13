"""All VA/MD/PA places for VMP scraping (224 places).

Virginia: 95 counties + 38 independent cities = 133
Maryland: 23 counties + Baltimore City = 24
Pennsylvania: 67 counties
"""

from __future__ import annotations

# id (no spaces) -> {name, state, unit: county|city}
PLACES: dict[str, dict[str, str]] = {}


def _add(state: str, items: list[tuple[str, str]], unit: str) -> None:
    for pid, name in items:
        key = f"{state}:{pid}"
        PLACES[key] = {"id": pid, "name": name, "state": state, "unit": unit}


# --- Virginia: 95 counties ---
_add(
    "VA",
    [
        ("Accomack", "Accomack"),
        ("Albemarle", "Albemarle"),
        ("Alleghany", "Alleghany"),
        ("Amelia", "Amelia"),
        ("Amherst", "Amherst"),
        ("Appomattox", "Appomattox"),
        ("Arlington", "Arlington"),
        ("Augusta", "Augusta"),
        ("Bath", "Bath"),
        ("Bedford", "Bedford"),
        ("Bland", "Bland"),
        ("Botetourt", "Botetourt"),
        ("Brunswick", "Brunswick"),
        ("Buchanan", "Buchanan"),
        ("Buckingham", "Buckingham"),
        ("Campbell", "Campbell"),
        ("Caroline", "Caroline"),
        ("Carroll", "Carroll"),
        ("CharlesCity", "Charles City"),
        ("Charlotte", "Charlotte"),
        ("Chesterfield", "Chesterfield"),
        ("Clarke", "Clarke"),
        ("Craig", "Craig"),
        ("Culpeper", "Culpeper"),
        ("Cumberland", "Cumberland"),
        ("Dickenson", "Dickenson"),
        ("Dinwiddie", "Dinwiddie"),
        ("Essex", "Essex"),
        ("Fairfax", "Fairfax"),
        ("Fauquier", "Fauquier"),
        ("Floyd", "Floyd"),
        ("Fluvanna", "Fluvanna"),
        ("Franklin", "Franklin"),
        ("Frederick", "Frederick"),
        ("Giles", "Giles"),
        ("Gloucester", "Gloucester"),
        ("Goochland", "Goochland"),
        ("Grayson", "Grayson"),
        ("Greene", "Greene"),
        ("Greensville", "Greensville"),
        ("Halifax", "Halifax"),
        ("Hanover", "Hanover"),
        ("Henrico", "Henrico"),
        ("Henry", "Henry"),
        ("Highland", "Highland"),
        ("IsleOfWight", "Isle of Wight"),
        ("JamesCity", "James City"),
        ("KingAndQueen", "King and Queen"),
        ("KingGeorge", "King George"),
        ("KingWilliam", "King William"),
        ("Lancaster", "Lancaster"),
        ("Lee", "Lee"),
        ("Loudoun", "Loudoun"),
        ("Louisa", "Louisa"),
        ("Lunenburg", "Lunenburg"),
        ("Madison", "Madison"),
        ("Mathews", "Mathews"),
        ("Mecklenburg", "Mecklenburg"),
        ("Middlesex", "Middlesex"),
        ("Montgomery", "Montgomery"),
        ("Nelson", "Nelson"),
        ("NewKent", "New Kent"),
        ("Northampton", "Northampton"),
        ("Northumberland", "Northumberland"),
        ("Nottoway", "Nottoway"),
        ("Orange", "Orange"),
        ("Page", "Page"),
        ("Patrick", "Patrick"),
        ("Pittsylvania", "Pittsylvania"),
        ("Powhatan", "Powhatan"),
        ("PrinceEdward", "Prince Edward"),
        ("PrinceGeorge", "Prince George"),
        ("PrinceWilliam", "Prince William"),
        ("Pulaski", "Pulaski"),
        ("Rappahannock", "Rappahannock"),
        ("Richmond", "Richmond"),
        ("Roanoke", "Roanoke"),
        ("Rockbridge", "Rockbridge"),
        ("Rockingham", "Rockingham"),
        ("Russell", "Russell"),
        ("Scott", "Scott"),
        ("Shenandoah", "Shenandoah"),
        ("Smyth", "Smyth"),
        ("Southampton", "Southampton"),
        ("Spotsylvania", "Spotsylvania"),
        ("Stafford", "Stafford"),
        ("Surry", "Surry"),
        ("Sussex", "Sussex"),
        ("Tazewell", "Tazewell"),
        ("Warren", "Warren"),
        ("Washington", "Washington"),
        ("Westmoreland", "Westmoreland"),
        ("Wise", "Wise"),
        ("Wythe", "Wythe"),
        ("York", "York"),
    ],
    "county",
)

# --- Virginia: 38 independent cities (unit=city; queries omit County) ---
_add(
    "VA",
    [
        ("Alexandria", "Alexandria"),
        ("Bristol", "Bristol"),
        ("BuenaVista", "Buena Vista"),
        ("Charlottesville", "Charlottesville"),
        ("Chesapeake", "Chesapeake"),
        ("ColonialHeights", "Colonial Heights"),
        ("Covington", "Covington"),
        ("Danville", "Danville"),
        ("Emporia", "Emporia"),
        ("FairfaxCity", "Fairfax"),
        ("FallsChurch", "Falls Church"),
        ("FranklinCity", "Franklin"),
        ("Fredericksburg", "Fredericksburg"),
        ("Galax", "Galax"),
        ("Hampton", "Hampton"),
        ("Harrisonburg", "Harrisonburg"),
        ("Hopewell", "Hopewell"),
        ("Lexington", "Lexington"),
        ("Lynchburg", "Lynchburg"),
        ("Manassas", "Manassas"),
        ("ManassasPark", "Manassas Park"),
        ("Martinsville", "Martinsville"),
        ("NewportNews", "Newport News"),
        ("Norfolk", "Norfolk"),
        ("Norton", "Norton"),
        ("Petersburg", "Petersburg"),
        ("Poquoson", "Poquoson"),
        ("Portsmouth", "Portsmouth"),
        ("Radford", "Radford"),
        ("RichmondCity", "Richmond"),
        ("RoanokeCity", "Roanoke"),
        ("Salem", "Salem"),
        ("Staunton", "Staunton"),
        ("Suffolk", "Suffolk"),
        ("VirginiaBeach", "Virginia Beach"),
        ("Waynesboro", "Waynesboro"),
        ("Williamsburg", "Williamsburg"),
        ("Winchester", "Winchester"),
    ],
    "city",
)

# --- Maryland: 23 counties ---
_add(
    "MD",
    [
        ("Allegany", "Allegany"),
        ("AnneArundel", "Anne Arundel"),
        ("Baltimore", "Baltimore"),
        ("Calvert", "Calvert"),
        ("Caroline", "Caroline"),
        ("Carroll", "Carroll"),
        ("Cecil", "Cecil"),
        ("Charles", "Charles"),
        ("Dorchester", "Dorchester"),
        ("Frederick", "Frederick"),
        ("Garrett", "Garrett"),
        ("Harford", "Harford"),
        ("Howard", "Howard"),
        ("Kent", "Kent"),
        ("Montgomery", "Montgomery"),
        ("PrinceGeorges", "Prince George's"),
        ("QueenAnnes", "Queen Anne's"),
        ("Somerset", "Somerset"),
        ("StMarys", "St. Mary's"),
        ("Talbot", "Talbot"),
        ("Washington", "Washington"),
        ("Wicomico", "Wicomico"),
        ("Worcester", "Worcester"),
    ],
    "county",
)

# --- Maryland: Baltimore City ---
_add(
    "MD",
    [
        ("BaltimoreCity", "Baltimore"),
    ],
    "city",
)

# --- Pennsylvania: 67 counties ---
_add(
    "PA",
    [
        ("Adams", "Adams"),
        ("Allegheny", "Allegheny"),
        ("Armstrong", "Armstrong"),
        ("Beaver", "Beaver"),
        ("Bedford", "Bedford"),
        ("Berks", "Berks"),
        ("Blair", "Blair"),
        ("Bradford", "Bradford"),
        ("Bucks", "Bucks"),
        ("Butler", "Butler"),
        ("Cambria", "Cambria"),
        ("Cameron", "Cameron"),
        ("Carbon", "Carbon"),
        ("Centre", "Centre"),
        ("Chester", "Chester"),
        ("Clarion", "Clarion"),
        ("Clearfield", "Clearfield"),
        ("Clinton", "Clinton"),
        ("Columbia", "Columbia"),
        ("Crawford", "Crawford"),
        ("Cumberland", "Cumberland"),
        ("Dauphin", "Dauphin"),
        ("Delaware", "Delaware"),
        ("Elk", "Elk"),
        ("Erie", "Erie"),
        ("Fayette", "Fayette"),
        ("Forest", "Forest"),
        ("Franklin", "Franklin"),
        ("Fulton", "Fulton"),
        ("Greene", "Greene"),
        ("Huntingdon", "Huntingdon"),
        ("Indiana", "Indiana"),
        ("Jefferson", "Jefferson"),
        ("Juniata", "Juniata"),
        ("Lackawanna", "Lackawanna"),
        ("Lancaster", "Lancaster"),
        ("Lawrence", "Lawrence"),
        ("Lebanon", "Lebanon"),
        ("Lehigh", "Lehigh"),
        ("Luzerne", "Luzerne"),
        ("Lycoming", "Lycoming"),
        ("McKean", "McKean"),
        ("Mercer", "Mercer"),
        ("Mifflin", "Mifflin"),
        ("Monroe", "Monroe"),
        ("Montgomery", "Montgomery"),
        ("Montour", "Montour"),
        ("Northampton", "Northampton"),
        ("Northumberland", "Northumberland"),
        ("Perry", "Perry"),
        ("Philadelphia", "Philadelphia"),
        ("Pike", "Pike"),
        ("Potter", "Potter"),
        ("Schuylkill", "Schuylkill"),
        ("Snyder", "Snyder"),
        ("Somerset", "Somerset"),
        ("Sullivan", "Sullivan"),
        ("Susquehanna", "Susquehanna"),
        ("Tioga", "Tioga"),
        ("Union", "Union"),
        ("Venango", "Venango"),
        ("Warren", "Warren"),
        ("Washington", "Washington"),
        ("Wayne", "Wayne"),
        ("Westmoreland", "Westmoreland"),
        ("Wyoming", "Wyoming"),
        ("York", "York"),
    ],
    "county",
)

assert len([k for k in PLACES if k.startswith("VA:") and PLACES[k]["unit"] == "county"]) == 95
assert len([k for k in PLACES if k.startswith("VA:") and PLACES[k]["unit"] == "city"]) == 38
assert len([k for k in PLACES if k.startswith("VA:")]) == 133
assert len([k for k in PLACES if k.startswith("MD:") and PLACES[k]["unit"] == "county"]) == 23
assert len([k for k in PLACES if k.startswith("MD:") and PLACES[k]["unit"] == "city"]) == 1
assert len([k for k in PLACES if k.startswith("MD:")]) == 24
assert len([k for k in PLACES if k.startswith("PA:")]) == 67
assert len(PLACES) == 224

PRIORITY = [
    "VA:Fairfax",
    "VA:Loudoun",
    "VA:PrinceWilliam",
    "VA:Arlington",
    "VA:VirginiaBeach",
    "VA:Norfolk",
    "VA:Chesapeake",
    "VA:RichmondCity",
    "VA:Henrico",
    "VA:Chesterfield",
    "VA:Alexandria",
    "VA:NewportNews",
    "VA:Hampton",
    "VA:Stafford",
    "VA:Spotsylvania",
    "VA:Hanover",
    "VA:RoanokeCity",
    "VA:Lynchburg",
    "MD:Montgomery",
    "MD:PrinceGeorges",
    "MD:Baltimore",
    "MD:BaltimoreCity",
    "MD:AnneArundel",
    "MD:Howard",
    "MD:Harford",
    "MD:Frederick",
    "MD:Carroll",
    "MD:Charles",
    "PA:Philadelphia",
    "PA:Allegheny",
    "PA:Montgomery",
    "PA:Bucks",
    "PA:Delaware",
    "PA:Chester",
    "PA:Lancaster",
    "PA:York",
    "PA:Lehigh",
    "PA:Northampton",
    "PA:Berks",
    "PA:Erie",
    "PA:Dauphin",
    "PA:Lackawanna",
    "PA:Westmoreland",
    "PA:Luzerne",
    "PA:Cumberland",
]

QUERY_TEMPLATES = {
    "county": [
        "real estate developer {name} County {st}",
        "land developer {name} County {st}",
        "home builder {name} County {st}",
    ],
    "city": [
        "real estate developer {name} {st}",
        "land developer {name} {st}",
        "home builder {name} {st}",
    ],
}

_ALIASES = {
    "charlescity": "CharlesCity",
    "isleofwight": "IsleOfWight",
    "jamescity": "JamesCity",
    "kingandqueen": "KingAndQueen",
    "kinggeorge": "KingGeorge",
    "kingwilliam": "KingWilliam",
    "newkent": "NewKent",
    "princeedward": "PrinceEdward",
    "princegeorge": "PrinceGeorge",
    "princewilliam": "PrinceWilliam",
    "buenavista": "BuenaVista",
    "colonialheights": "ColonialHeights",
    "fairfaxcity": "FairfaxCity",
    "fallschurch": "FallsChurch",
    "franklincity": "FranklinCity",
    "manassaspark": "ManassasPark",
    "newportnews": "NewportNews",
    "richmondcity": "RichmondCity",
    "roanokecity": "RoanokeCity",
    "virginiabeach": "VirginiaBeach",
    "annearundel": "AnneArundel",
    "princegeorges": "PrinceGeorges",
    "queenannes": "QueenAnnes",
    "stmarys": "StMarys",
    "baltimorecity": "BaltimoreCity",
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

    state_order = ("VA", "MD", "PA")
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
    for st in ("VA", "MD", "PA"):
        print(f"  {st}={sum(1 for p in PLACES if p.startswith(f'{st}:'))}")
    print("next:", remaining(set())[:8])
    # spot-check city vs county disambiguation
    assert queries_for("VA:Fairfax")[0] == "real estate developer Fairfax County VA"
    assert queries_for("VA:FairfaxCity")[0] == "real estate developer Fairfax VA"
    assert queries_for("MD:Baltimore")[0] == "real estate developer Baltimore County MD"
    assert queries_for("MD:BaltimoreCity")[0] == "real estate developer Baltimore MD"
