from countries_by_regions import REGIONS

CONVENTIONS = {
    "vienna": (
        [c for c in REGIONS["Europe"] if c != "Ireland"] +
        ["Curaçao", "Ecuador", "Réunion"] +
        ["Bangladesh", "India", "Pakistan", "Singapore", "Vietnam",
         "Kazakhstan", "Kyrgyzstan", "Mongolia"] +
        REGIONS["Africa"] +
        REGIONS["MiddleEast"]
    ),
    "mutcd": (
        ["Bermuda", "Canada", "United States of America",
         "Costa Rica", "Guatemala", "Panama",
         "Puerto Rico", "U.S. Virgin Islands"] +
        REGIONS["Oceania"]
    ),
    "hybrid": (
        ["Ireland"] +
        ["Argentina", "Bolivia", "Brazil", "Chile", "Colombia",
         "Dominican Republic", "Mexico", "Peru", "Uruguay"] +
        ["Bhutan", "Cambodia", "Indonesia", "Laos", "Malaysia",
         "Philippines", "Sri Lanka", "Thailand",
         "China", "Hong Kong", "Japan", "South Korea", "Taiwan"]
    ),
}


# Reverse lookup: country → convention:
# CONVENTIONS["vienna"]           # → full vienna list
# COUNTRY_CONVENTION["France"]    # → "vienna"
COUNTRY_CONVENTION = {
    country: convention
    for convention, countries in CONVENTIONS.items()
    for country in countries
}