"""
Alberta 2026 Referendum - extract unofficial/official results from Elections Alberta
and write Power BI-ready CSVs (star schema).

Usage:  python ab_referendum_extract.py            (writes to .\\alberta_referendum_2026)
        python ab_referendum_extract.py C:\\path\\to\\output
"""
import csv
import os
import re
import sys
import time
from collections import Counter

import requests

SITE = "https://results.elections.ab.ca"
ELECTION_ID = "8400"          # the number at the end of the results page URL
API_VERSION = "3.3.1"         # sent by the site's own JavaScript; harmless if it changes
OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "alberta_referendum_2026"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (personal Power BI project)",
    "Accept": "application/json, text/plain, */*",
    "Referer": f"{SITE}/{ELECTION_ID}",
}

VOTE_TYPES = {"ORD": "Election Day", "ADV": "Advance", "MOB": "Mobile", "VBMHQ": "Special Ballot"}

# Ballot number -> (API questionID, category, short name, yes label, no label)
QUESTIONS = {
    1: (1, "Immigration & social programs", "Increase provincial control over immigration", "Yes", "No"),
    2: (2, "Immigration & social programs", "Limit provincial programs by immigration status", "Yes", "No"),
    3: (3, "Immigration & social programs", "12-month residency for social supports", "Yes", "No"),
    4: (4, "Immigration & social programs", "Health/education fee for non-permanent residents", "Yes", "No"),
    5: (5, "Elections", "Proof of citizenship to vote", "Yes", "No"),
    6: (6, "Constitutional", "Provinces select superior court justices", "Yes", "No"),
    7: (7, "Constitutional", "Abolish the Senate", "Yes", "No"),
    8: (8, "Constitutional", "Opt out of federal programs with funding", "Yes", "No"),
    9: (9, "Constitutional", "Provincial law priority over federal law", "Yes", "No"),
    10: (11, "Independence", "Remain in Canada vs. start separation referendum process",
         "Option 1: Remain in Canada", "Option 2: Begin separation referendum process"),
}

session = requests.Session()
session.headers.update(HEADERS)


def get_data(questions="", wards=""):
    """Call the same JSON endpoint the results page uses."""
    url = f"{SITE}/data/{ELECTION_ID}"
    params = {"version": API_VERSION, "questions": questions, "wards": wards}
    for attempt in range(3):
        r = session.get(url, params=params, timeout=60)
        if r.status_code == 200:
            body = r.json()
            if not body.get("success"):
                raise RuntimeError(f"API returned success=false for {r.url}")
            return body
        print(f"  HTTP {r.status_code} on attempt {attempt + 1}, retrying...")
        time.sleep(5)
    r.raise_for_status()


def get_division_names():
    """Division names are not in the JSON; they are in the page HTML as 'NN - Name'."""
    html = session.get(f"{SITE}/{ELECTION_ID}", timeout=60).text
    names = {}
    for code, name in re.findall(r"\b(\d{2}) - ([A-Za-z][A-Za-z .'\-]+?)\s*<", html):
        names.setdefault(code, name.strip())
    return names


def area_of(name):
    if name.startswith("Calgary"):
        return "Calgary"
    if name.startswith("Edmonton"):
        return "Edmonton"
    return "Rest of Alberta"


def write_csv(name, header, rows):
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  wrote {name} ({len(rows):,} rows)")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("1/4 Summary call...")
    summary = get_data()
    ref = summary["referendumResults"]
    last_updated = summary["lastUpdated"]
    wards = ref["wards"]                                  # [{ward, pollsReporting, totalPolls}]
    ward_codes = sorted(w["ward"] for w in wards)
    print(f"  last updated {last_updated}; {len(ward_codes)} divisions; "
          f"{ref['widgets']['summary']['pollsReporting']} of {ref['widgets']['summary']['totalPolls']} locations reported")

    print("2/4 Division names...")
    names = get_division_names()
    missing = [c for c in ward_codes if c not in names]
    if missing:
        print(f"  WARNING: no name found for {len(missing)} divisions: {missing[:10]}")

    print("3/4 Results per question (one call each, all divisions)...")
    loc_index = {}          # (division, vote type, location name) -> LocationKey
    locations = []
    fact_loc, fact_div = [], []
    for qno, (qid, *_rest) in QUESTIONS.items():
        body = get_data(questions=str(qid), wards=",".join(ward_codes))
        stats = next(q for q in body["referendumResults"]["votes"]["questionStats"] if q["questionID"] == qid)
        for ws in stats["wardStats"]:
            fact_div.append([qno, ws["ward"], ws["yesVotes"], ws["noVotes"]])
            for p in ws["pollStats"]:
                key = (ws["ward"], p["pollTypeCode"], p["pollName"])
                if key not in loc_index:
                    loc_index[key] = len(locations)
                    locations.append(key)
                y, n = p["yesVotes"], p["noVotes"]
                reported = int(y is not None and n is not None)
                fact_loc.append([qno, loc_index[key], ws["ward"], p["pollTypeCode"],
                                 "" if y is None else y, "" if n is None else n, reported])
        print(f"  Q{qno}: {len(stats['wardStats'])} divisions")
        time.sleep(1)       # be polite to the server

    print("4/4 Writing CSVs...")
    write_csv("dim_question.csv",
              ["QuestionNo", "SourceQuestionID", "Category", "ShortName", "YesLabel", "NoLabel"],
              [[qno, *vals] for qno, vals in QUESTIONS.items()])
    rep = {w["ward"]: w for w in wards}
    write_csv("dim_electoral_division.csv",
              ["DivisionCode", "DivisionName", "DivisionLabel", "Area", "VotingLocationsReporting", "VotingLocationsTotal"],
              [[c, names.get(c, ""), f"{c} - {names.get(c, '')}", area_of(names.get(c, "")),
                rep[c]["pollsReporting"], rep[c]["totalPolls"]] for c in ward_codes])
    write_csv("dim_voting_location.csv",
              ["LocationKey", "DivisionCode", "VoteTypeCode", "VoteType", "LocationName"],
              [[i, d, t, VOTE_TYPES.get(t, t), n] for i, (d, t, n) in enumerate(locations)])
    write_csv("fact_results_by_location.csv",
              ["QuestionNo", "LocationKey", "DivisionCode", "VoteTypeCode", "YesVotes", "NoVotes", "Reported"],
              fact_loc)
    write_csv("fact_results_by_division.csv", ["QuestionNo", "DivisionCode", "YesVotes", "NoVotes"], fact_div)
    with open(os.path.join(OUT_DIR, "_last_updated.txt"), "w") as f:
        f.write(last_updated)

    # ---- validation ----
    print("Validation:")
    sums = Counter()
    for qno, _, d, _, y, n, _ in fact_loc:
        sums[(qno, d, "y")] += y or 0
        sums[(qno, d, "n")] += n or 0
    bad = [r for r in fact_div if sums[(r[0], r[1], "y")] != r[2] or sums[(r[0], r[1], "n")] != r[3]]
    print(f"  division rows that don't match location sums: {len(bad)} (expect 0)")
    print(f"  locations: {len(locations):,}  fact rows: {len(fact_loc):,} (expect locations x 10)")
    print(f"  unreported location rows: {sum(1 for r in fact_loc if r[6] == 0)}")
    for qno in QUESTIONS:
        y = sum(r[2] for r in fact_div if r[0] == qno)
        n = sum(r[3] for r in fact_div if r[0] == qno)
        print(f"  Q{qno:>2}: yes {y:>10,}  no {n:>10,}  yes% {100 * y / (y + n):5.1f}")


if __name__ == "__main__":
    main()
