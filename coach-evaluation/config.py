"""Configuration for the coach-evaluation collection scripts."""

WIKI = "nl.wikipedia.org"
API_URL = f"https://{WIKI}/w/api.php"

# Subject of the evaluation (on-wiki username).
SUBJECT_USER = "10Guillot"

# Mentor / coach usernames. Interactions with these users are split out from
# general community interaction in the report.
MENTOR_USERS: list[str] = ["Bob.v.R"]

# Wikimedia's User-Agent policy requires a descriptive UA with contact + purpose.
USER_AGENT = (
    "WikimediaResearch/1.0 (lodewijk@stanford.edu; "
    "ArbCom coach evaluation data collection)"
)

# Back off automatically when the cluster is lagged (good-citizen setting).
MAXLAG = 5

# Delay between paginated API calls, seconds.
REQUEST_DELAY = 0.5

# An edit counts as a "significant expansion" of an existing article when a
# single edit adds at least SINGLE_EDIT_BYTES, or the cumulative net addition
# across all of the subject's edits to that page reaches CUMULATIVE_BYTES.
SINGLE_EDIT_BYTES = 2000
CUMULATIVE_BYTES = 4000

DATA_DIR = "data"
ARTICLES_MD = "articles_under_review.md"
INTERACTIONS_MD = "interactions_since_unblock.md"
