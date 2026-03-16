# Block Analysis: Understanding the IP Blocking Landscape on Wikimedia Projects

## Project summary

This project maps the current landscape of active IP and range blocks on a given Wikimedia project — initially focused on nl.wikipedia.org — with the aim of better understanding who these blocks affect in practice, particularly hypothetical new contributors: anonymous editors and newly registered accounts.

IP and range blocks are an important tool for protecting wikis from vandalism and abuse. At the same time, because many IP addresses are shared (by households, schools, mobile carriers, or internet service providers), a block placed for one reason may also affect unrelated users who happen to share the same address or range. This project does not evaluate whether individual blocks were the right decision; rather, it seeks to describe the overall landscape in a structured way, so that the community can make informed choices about blocking policy.

This is the first step in a longer research project. The immediate goal is to build a clean, reusable dataset of active blocks, enriched with metadata and independent IP-type classification, that can inform future analysis and community discussion.

---

## Design principles

### Wiki-agnostic
The code is written to work with any Wikimedia project. The target wiki (or list of wikis) is a configurable parameter (e.g., `nlwiki`, `enwiki`, `dewiki`). All API endpoints are constructed dynamically. Initial analysis and examples use nl.wikipedia.org, but the pipeline can be run against any wiki or a set of wikis in a single run.

### Repeatable snapshots
The pipeline is designed to be rerun on a regular cadence (e.g., weekly or monthly). Each run produces a timestamped snapshot of the block landscape at that point in time. Snapshots are stored with a `snapshot_date` and `wiki` identifier, so that runs across different wikis and different weeks can be loaded together and compared. This allows longitudinal questions such as: *How has the distribution of block types changed over time? Did a policy change shift the balance of preventive versus responsive blocks?*

---

## Scope

### Blocks included
- **Local blocks**: IP and range blocks issued by administrators of the target wiki
- **Global blocks**: blocks issued centrally by Wikimedia stewards that also apply to the target wiki
- Both types are included in the dataset and clearly distinguished using a `block_scope` field (`local` / `global`)

### New contributors
"New contributor" is treated as a hypothetical: any person who might attempt to edit the wiki without an established, trusted account. This includes anonymous (IP) editors and newly registered accounts that have not yet gained elevated permissions. No specific threshold (edit count or account age) is applied — the focus is on the blocking landscape that any newcomer could encounter.

### Block flags
All active blocks are collected regardless of flags. Key flags such as `anononly` (affects only anonymous users, not logged-in accounts) are retained as metadata fields, since they affect whether a block impacts registered newcomers as well as anonymous editors.

---

## Data to collect

### Per block
| Field | Description |
|---|---|
| `snapshot_date` | Date this snapshot was collected (ISO 8601) |
| `wiki` | Wiki identifier (e.g., `nlwiki`, `enwiki`) |
| `block_id` | Unique block identifier |
| `block_scope` | `local` or `global` |
| `target` | Blocked IP address or CIDR range |
| `is_range_block` | Boolean |
| `range_size` | Number of addresses covered (computed from CIDR notation) |
| `blocked_by` | Username of the administrator who placed the block |
| `timestamp` | When the block was placed |
| `expiry` | Expiry timestamp, or `infinite` |
| `duration_days` | Computed duration in days (null if infinite) |
| `reason_text` | Raw block reason as entered by the administrator |
| `anononly` | Boolean — block applies to anonymous users only |
| `nocreate` | Boolean — account creation is blocked |
| `noemail` | Boolean — email sending is blocked |

### Derived characterization fields
| Field | Description |
|---|---|
| `stated_reason_category` | Category of block reason as written by the administrator, extracted from `reason_text` via keyword/pattern matching (e.g., `open_proxy`, `school`, `mobile`, `tor`, `vandalism`, `spam`, `unknown`) |
| `block_intent` | Whether the block appears to be preventive (placed based on the nature of the IP, before or without a specific incident) or responsive (placed in response to a specific edit or pattern of behaviour) — inferred from `reason_text` |
| `ip_type_independent` | IP/range type as determined independently by an external IP intelligence source (e.g., `residential`, `mobile`, `education`, `hosting/datacenter`, `proxy/vpn`, `unknown`) |
| `ip_org` | Organization name from WHOIS/ASN data |
| `ip_asn` | Autonomous System Number |
| `ip_country` | Country of IP registration |

---

## IP type classification

Raw WHOIS data (organization name and ASN) is collected as a baseline reference. However, the more analytically useful output is a **categorical IP type** such as `residential`, `mobile`, `education`, `hosting`, or `proxy/vpn`.

For this, a dedicated IP intelligence library or API is preferred over raw WHOIS, as these sources are specifically designed to return connection-type classifications. Candidates to evaluate:
- **ipinfo.io** — returns ASN, organization, and a connection `type` field (residential, mobile, hosting, etc.)
- **ip-api.com** — free tier returns organization, ASN, and proxy/hosting flags
- **MaxMind GeoIP2** — returns connection type (residential, corporate, mobile, etc.)

The best-fit source will be selected based on coverage, ease of use, and free-tier limits. The `ip_type_independent` field is the primary target; `ip_org` is a supporting and fallback signal.

---

## Stated reason category

The `stated_reason_category` field reflects how the blocking administrator described the block at the time it was placed — based on the wording in `reason_text`. This is not an evaluation of whether the characterization was correct; it is simply a structured reading of the stated reason, used to compare with the independently determined `ip_type_independent`.

Comparing these two fields across the dataset may reveal patterns where the stated reason category and the independently determined IP type diverge. Such divergences are expected and understandable: IP address assignments change over time, and administrators often act quickly with the information available to them. The goal of surfacing these cases is to help the community identify where updated information might be useful, not to assign fault.

---

## Block intent classification

Determined primarily from `reason_text` pattern matching:
- **Preventive**: the reason references the nature of the IP address or range (e.g., a known proxy service, hosting provider, Tor exit node, or VPN) without referencing a specific edit or user incident
- **Responsive**: the reason references a specific edit, diff, user, page, or pattern of recent behaviour

A third value (`unclear`) is used when the reason is absent, too generic, or ambiguous.

---

## Data storage

Each pipeline run produces a timestamped snapshot file, named by wiki and date (e.g., `blocks_nlwiki_2026-03-16.csv`). Snapshot files follow a consistent schema so they can be concatenated across runs and wikis into a single dataset for longitudinal or cross-wiki analysis. The `snapshot_date` and `wiki` fields serve as the composite key for each run.

Raw and enriched data are both saved, so that derived fields (such as `stated_reason_category` or `ip_type_independent`) can be recomputed or updated without re-querying the API.

---

## Scouting task: historical data availability

Before deciding whether to also collect historical blocks (from the block log), a scouting step is needed to answer:

> **Is reliable IP type classification available for historical time points?**

Most IP intelligence databases return *current* classifications. If a range's usage has changed over the years (for example, from a residential ISP to a hosting provider), applying today's classification to older blocks may be misleading. The scouting step should determine:
- Whether any IP intelligence source provides historical snapshots
- If not, whether the current classification is a reasonable approximation for recent years
- Whether the block log API (`list=logevents&letype=block`) provides sufficient historical data for trend analysis

The answer to this scouting task will determine whether collecting historical blocks is a worthwhile next step.

---

## Technical approach

### Project structure

Data collection and enrichment are implemented as a set of importable Python modules. A Jupyter notebook handles configuration, orchestration, and all visualisation and analysis. This keeps the collection logic reusable and testable independently of the notebook.

Tentative module structure:

```
block analysis/
├── collect_blocks.py       # Fetch active local and global blocks via Wikimedia API
├── enrich_ip.py            # Query IP intelligence source; add ip_type_independent, ip_org, ip_asn, ip_country
├── classify_reasons.py     # Pattern-match reason_text; derive stated_reason_category and block_intent
├── fetch_page.py           # Fetch the wikitext or parsed content of any wiki page by title via the API;
│                           #   useful for resolving page links referenced in block reasons
├── storage.py              # Save/load timestamped snapshot files (CSV/JSON)
├── config.py               # Wikis to query, API User-Agent, output paths, etc.
└── analysis.ipynb          # Calls the modules above; produces visualisations and summaries
```

### Other conventions
- All data fetched via the **Wikimedia API** (`action=query&list=blocks` for local blocks; GlobalBlocking API for global blocks)
- Target wiki(s) are configurable in `config.py`; no wiki is hardcoded elsewhere
- Each run is identified by wiki and date; output files are named and stored accordingly
- All API requests include a descriptive `User-Agent` header identifying the project and a contact address, in accordance with Wikimedia API guidelines
- IP intelligence queries made via a suitable Python library or API wrapper

---

## Next steps and open questions

- Finalise the taxonomy of `stated_reason_category` and `ip_type_independent` values (ideally informed by a first look at actual reason texts before coding)
- Select the IP intelligence source after a brief evaluation
- Complete the scouting task on historical data availability
- Longer-term: share findings with the wiki community to contribute to informed discussions about blocking practices and their effects on new contributors
