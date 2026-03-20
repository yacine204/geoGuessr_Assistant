REGIONS = {
    "Europe": [
        "Andorra", "Austria", "Belgium", "France", "Germany",
        "Greece", "Isle of Man", "Italy", "Luxembourg", "Malta",
        "Monaco", "Netherlands", "Portugal", "Spain", "Switzerland",
        "United Kingdom", "Albania", "Bulgaria", "Croatia",
        "Czech Republic", "Hungary", "Montenegro", "North Macedonia",
        "Poland", "Romania", "Russia", "Serbia", "Slovakia",
        "Slovenia", "Ukraine", "Denmark", "Faroe Islands", "Finland",
        "Greenland", "Iceland", "Norway", "Sweden",
        "Estonia", "Latvia", "Lithuania", "Ireland",
    ],
    "Americas": [
        "Bermuda", "Canada", "United States of America",
        "Puerto Rico", "U.S. Virgin Islands",
        "Mexico", "Costa Rica", "Guatemala", "Panama",
        "Dominican Republic",
        "Argentina", "Bolivia", "Brazil", "Chile", "Colombia",
        "Curaçao", "Ecuador", "Peru", "Uruguay",
    ],
    "Asia": [
        "Bangladesh", "Bhutan", "Cambodia", "India", "Indonesia",
        "Japan", "Kazakhstan", "Kyrgyzstan", "Laos", "Malaysia",
        "Mongolia", "Pakistan", "Philippines", "Singapore",
        "South Korea", "Sri Lanka", "Taiwan", "Thailand", "Vietnam",
        "China", "Hong Kong",
    ],
    "MiddleEast": [
        "Israel", "Jordan", "Palestine", "Qatar",
        "Tunisia", "Turkey", "United Arab Emirates",
    ],
    "Africa": [
        "Botswana", "Eswatini", "Ghana", "Kenya", "Lesotho",
        "Madagascar", "Nigeria", "Réunion", "Rwanda", "Senegal",
        "South Africa", "Uganda",
    ],
    "Oceania": [
        "American Samoa", "Australia", "Christmas Island",
        "Guam", "New Zealand", "Northern Mariana Islands",
        "U.S. Minor Outlying Islands",
    ],
}

# Reverse lookup: country → region:
# COUNTRY_REGION["France"] : europe
# COUNTRY_REGION["Europe"] : list of europe countries
COUNTRY_REGION = {
    country: region
    for region, countries in REGIONS.items()
    for country in countries
}
