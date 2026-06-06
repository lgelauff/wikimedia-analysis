# Claims Document v2 — AI Effects on the Knowledge Ecosystem
**Date:** 2026-03-18
**Status:** Draft for review
**Covers:** Wave 1 themes A–H + Wave 3 EC themes

---

## Theme A — Changing Information-Seeking Behaviour

**A1** [strong]
Since the launch of AI search features (Google AI Overviews, ChatGPT, Perplexity), click-through rates on traditional search results have declined significantly: Pew Research (March 2025, ~900 U.S. adults, behavioural tracking data) found that when an AI summary is present, click-through on traditional results falls from 15% to 8%, and session abandonment rises from 16% to 26%. Only 1% of sessions result in a click on sources cited within AI summaries. AI chatbots and search summaries are increasingly used as the primary interface for information lookup, bypassing the source websites that created the content.
Sources: pew2025click, aral2026rise, khosravi2026impact, delriochanona2024large
Gap: The opening framing ("click-through rates have declined") implies a longitudinal trend, but pew2025click is a March 2025 cross-sectional study — it compares sessions with and without AI summaries at one point in time, not before-vs.-after. It does not measure what CTR was before AI Overviews. aral2026rise and khosravi2026impact do not provide CTR data and should not be co-cited for this specific finding. "AI chatbots and search summaries are increasingly used as the primary interface" is a conclusion not directly supported by the Pew data (U.S.-only, March 2025, opted-in tracking panel). Separately, Semrush data in adexchanger2026aisearch shows zero-click rates on AI Overview keywords dropped from 45% to 38% between January and October 2025 — a partial trend reversal that complicates the declining-CTR narrative.

**A2** [partial]
AI search tools systematically restructure which sources users encounter: a study of 24,000 search queries across 243 countries found that AI search surfaces fewer long-tail sources and more low-credibility or politically skewed content than traditional search, while accelerating decision-making and collapsing scrutiny. This re-centralises information flows toward a small number of AI synthesisers, shrinking the diversity of voices users encounter.
Sources: aral2026rise, simon2025generative
Gap: No source directly measures the share of total information queries now handled by standalone AI chatbots (as opposed to AI-augmented search) globally. simon2025generative (Reuters Institute) is a survey of news consumption attitudes across six countries — it does not measure source diversity or credibility of AI search results, and is misallocated here; it belongs with EC-5 or H-theme claims. The "re-centralises toward a small number of AI synthesisers" conclusion goes further than aral2026rise, which documents AI surfacing fewer long-tail sources, not that the AI synthesiser itself becomes the user's primary information voice.

**A3** [partial]
Pew Research (March 2025) found that only 1% of users click on sources cited within AI search summaries, providing a behavioural proxy for source awareness: if 99% of users do not follow the cited source, they are functionally unaware of provenance even when attribution is formally present. A majority of AI search users do not appear to verify AI-generated answers against original sources.
Sources: pew2025click, aral2026rise
Gap: Direct measurement of user comprehension of AI source attribution is absent. The click rate is a behavioural proxy, not a direct measurement of awareness or intention. aral2026rise does not measure click-through on cited sources in AI summaries at all — it measures which sources AI surfaces and their content properties; remove or replace as a supporting source here. Not clicking a source is not the same as not verifying — users could check through a second search, direct URL, or prior knowledge; the "majority do not verify" conclusion overclaims what the behavioral data shows.

TODO: how does this compare to other sources. 
---

## Theme B — Platform Traffic Decline

**B1** [strong]
Wikipedia's human visitor numbers declined by approximately 8% year-on-year in 2024–25, after the Wikimedia Foundation revised its bot-detection methodology. A separate difference-in-differences study using the geographic rollout of Google AI Overviews as a natural experiment estimated a 15% reduction in daily Wikipedia traffic in markets where AI Overviews were active compared to control editions — the strongest causal design currently available for this claim.
Sources: wikimedia2025newuser, khosravi2026impact
Gap: The 8% figure comes from WMF's own revised methodology — WMF has a fundraising interest in documenting traffic decline and is not an independent source. The WMF report itself notes that the revised figure "has to be interpreted with care" due to bot-detection changes applied retroactively. The two statistics (8% all-editions all-causes vs. 15% AIO-specific English-Wikipedia causal estimate) measure different phenomena and should not be presented as mutually corroborating without clearly distinguishing them. The causal DiD estimate (Khosravi) is robust but a preprint; the identification strategy (English vs. non-English control editions) carries a parallel-trends assumption that has not been externally validated. Wikipedia traffic has been on a long-term plateau since the mobile era; whether the current decline is an AI-driven inflection or continuation of an existing trend is not resolved.

**B2** [strong]
Stack Overflow saw a 25% decline in weekly posts within six months of ChatGPT's public launch in November 2022, with activity falling across all experience levels. A parallel peer-reviewed study found the same ~25% relative decline and additionally documented that Reddit communities showed no comparable effect, suggesting the mechanism is AI substitution of the platform's Q&A function rather than a platform-agnostic shift.
Sources: delriochanona2024large, burtch2024consequences, borwankar2023unraveling

**B3** [partial]
A broad range of open knowledge platforms that provided data for large language model training are now experiencing measurable declines in human traffic. News publishers have been particularly affected: search traffic to news sites fell an estimated 15% in the year following Google AI Overviews' launch (Similarweb, via CJR), and the no-click share of news searches rose from 56% to nearly 69% over the same period. Advertising intelligence data confirms traffic displacement across publisher categories as AI-generated summaries absorb queries that previously drove click-throughs to source websites.
Sources: cjr2025aioverviews, adexchanger2026aisearch, wikimedia2025newuser, delriochanona2024large
Gap: Previously cited figures ("37 of top 50 U.S. news sites", specific outlet losses for Business Insider, CNN, and Forbes) were not traceable to any cited source and have been removed. The 15% decline figure is a Similarweb estimate reported via CJR, not a primary dataset. Causal attribution of all traffic declines to AI is not established — Facebook algorithm changes, post-pandemic normalisation, and editorial restructuring are confounds not controlled for. Audited revenue figures attributable specifically to AI-driven traffic loss remain unpublished.

---

## Theme C — Contributor Pipeline Erosion

**C1** [partial]
The Wikimedia Foundation has explicitly linked declining Wikipedia readership to reduced editor recruitment, citing the reader-to-editor conversion pathway: fewer readers encountering editable content means fewer discovering the ability to contribute and fewer new editors entering the pipeline. A peer-reviewed theoretical model (JASIST, 2025) formalises this as a self-reinforcing cycle: AI pervasion → contributors perceive efforts less necessary → withdrawal → staling content → further readership decline.
Sources: wikimedia2025newuser, wagner2025death, noroozian2025generative
Gap: No independent empirical measurement of the rate of change in the reader-to-editor conversion ratio is available. WMF's own statement has a fundraising interest; peer-reviewed corroboration of the empirical magnitude is absent.
TODO: not sure how strong a theoretical model is, without empirical data to back it up. 

**C2** [partial]
A natural experiment exploiting ChatGPT's November 2022 launch found that newly created, popular Wikipedia articles whose content substantially overlapped with ChatGPT's training topics showed evidence consistent with, but not yet statistically confirming, greater declines in both editing activity and page viewership than articles with dissimilar content. A 2025 peer-reviewed study found no aggregate decline in editing activity but documented slower growth in ChatGPT-available language editions relative to unavailable ones — suggesting a substitution dampening effect at the language-edition level rather than an absolute decline.
Sources: lyu2025wikipedia, wagner2025death, reeves2025wikipedia
Counter-sources: yeverechyahu2024impact (GitHub Copilot increased overall open-source contribution volume, though it shifted composition toward iterative rather than capability innovation)
Gap: lyu2025wikipedia's editing-decline finding is described by the authors as "suggestive but not statistically significant." reeves2025wikipedia (2025, peer-reviewed, Collective Intelligence/SAGE) finds no aggregate decline but slower growth in AI-exposed editions. The claim cannot currently be stated as an established causal finding and should be framed accordingly.

**C3** [partial]
AI-generated code submissions are flooding open source project contribution queues, shifting maintainer time from development and mentoring newcomers toward triage of low-quality automated submissions. GitHub has officially acknowledged this as an "Eternal September" problem — estimating that only approximately 1 in 10 AI-generated pull requests meets quality standards — and is developing kill-switch tooling for maintainers. The documented Matplotlib incident — an autonomous AI agent submitted a pull request, was rejected, and published a negative post about the maintainer — illustrates how AI submissions crowd out legitimate newcomer pathways.
Sources: github2025eternalseptember, socket2026ai, gitclear2025ai, harding2024coding
Gap: No systematic study has measured the share of open source "Good First Issue" uptake or mentorship time displaced by AI submissions at scale. github2025eternalseptember is GitHub's own institutional acknowledgment — first-party, but not an independent empirical study. socket2026ai remains a case study.

**C4** [partial]
The Stack Overflow contributor pipeline shows evidence of demand-side substitution: an ACM CHI 2024 study found that 52% of ChatGPT answers to Stack Overflow questions contained incorrect information, yet 35% of users still preferred ChatGPT's answers due to comprehensiveness and presentation style — meaning users are substituting the platform even when the AI answer is factually inferior. Users who never visit Stack Overflow never become Stack Overflow contributors.
Sources: khatibi2024stackoverflow, delriochanona2024large, burtch2024consequences, borwankar2023unraveling
Counter-sources: yeverechyahu2024impact
Gap: The final sentence — "users who never visit SO never become contributors" — is logically true but the causal step from substitution to contributor pipeline damage is inferred. khatibi2024stackoverflow measures preference in a controlled study; the population-level effect on contributor recruitment is extrapolated, not measured.

**C5** [partial]
Scientific peer review — the primary quality-control mechanism for knowledge production — is undergoing measurable AI-driven disruption. A stylometric analysis of ICLR 2024 found that at least 15.8% of reviews contained detectable LLM-generated content (russo2025aireviews). Prompt injection attacks embedded in submission PDFs have been documented that attempt to manipulate AI-assisted reviewers (lin2025promptinjection). AI adoption in academic writing has outpaced journal AI policies: analysis of 5.2 million papers found that while 70% of journals have AI policies, only ~0.1% of papers explicitly disclose AI use, creating a systemic transparency gap in the knowledge production pipeline (plos2025nhanes).
Sources: russo2025aireviews, lin2025promptinjection, plos2025nhanes
Gap: The 15.8% AI-review figure is a lower bound from stylometric detection; true rate is unknown. lin2025promptinjection documents prompt injection design intent but not confirmed successful manipulation outcomes. The transparency gap finding (he2025academic, removed from this claim) is a distinct sub-claim about disclosure compliance that belongs separately. The Wikipedia structural analogy is reasoned inference, not empirical evidence. plos2025nhanes first-author unverified.

---

## Theme D — Financial Sustainability of Knowledge Infrastructure

**D1** [partial]
The Wikimedia Foundation has noted that declining page traffic directly threatens donation revenue: the primary mechanism for individual donations — banners displayed to active readers — reaches fewer people as human visits fall. WMF's 2025 report explicitly links the ~8% year-on-year traffic decline to reduced editor recruitment and lower individual donation exposure.
Sources: wikimedia2025newuser, noroozian2025generative
Gap: No independent analysis of WMF financial accounts or donation trend data is currently in the source pool. WMF's own statement has a fundraising interest. The mechanism is documented but no verified revenue impact figure has been published.

**D2** [partial]
Across journalism, academic publishing, and open knowledge infrastructure, the mechanisms by which AI-driven traffic displacement translates into financial pressure are documented, but verified revenue impact figures attributable specifically to AI have not been published for any sector. News publishers' advertising-driven revenue models are most exposed: no-click share of news searches rose from 56% to 69% in the year following Google AI Overviews' launch, and publishers anticipate a further 43% traffic decline over three years.
Sources: cjr2025aioverviews, simon2025generative, newman2024digital, grimmelmann2026scraping, noroozian2025generative
Gap: No sector has published audited revenue figures attributable specifically to AI-driven traffic loss, as distinct from pre-existing structural decline (advertising model, paywalls). This is a priority gap.

**D3** [partial]
Academic and scientific repositories face compounding financial pressure from AI scraping: they absorb significant infrastructure costs from AI crawler traffic without receiving compensation, while simultaneously losing the human-visitor traffic that justifies hosting and maintaining open-access content. A COAR survey of 66 academic repository members found over 90% had experienced AI bot scraping, with approximately two-thirds suffering significant operational impacts.
Sources: vannoorden2025webscraping, wikimedia2025crawlers, noroozian2025generative
Gap: The COAR survey is voluntary, self-selected, and self-reported by an organisation representing the surveyed institutions — a compound source bias. "Significant operational impacts" is vague and unverified. "Compounding financial pressure" treats two separate pressures (infrastructure costs, lost traffic) as a demonstrated spiral; no published financial accounts confirm the claimed compound effect.

---

## Theme E — AI Scraping Harm to Knowledge Infrastructure

**E1** [partial]
AI bot traffic has imposed measurable infrastructure costs on open knowledge platforms. Wikimedia reported a 50% increase in bandwidth consumption on Commons since January 2024, driven primarily by AI training and inference bots. 65% of resource-intensive datacenter load is now attributable to automated crawlers rather than human readers. Wikimedia's 2025–26 operational plan targets a 20% reduction in scraper request rate and a 30% reduction in bandwidth to manage the burden.
Sources: wikimedia2025crawlers, vannoorden2025webscraping
Gap: All three headline figures (50% bandwidth increase, 65% crawler load, 20%/30% targets) come from a single WMF internal report. WMF has institutional incentives to document and publicise AI scraping costs in support of policy and licensing advocacy. The "driven primarily by AI bots" attribution requires distinguishing AI scrapers from search engine crawlers, archival bots, and academic scrapers — WMF's classification methodology is not independently verified. Downgraded from "strong" pending independent corroboration.

**E2** [strong]
Multiple academic and institutional repositories have experienced AI scraping volumes sufficient to trigger service disruption or emergency access restrictions. A COAR survey of 66 members found over 90% had experienced significant AI bot scraping. The post-DeepSeek surge in early 2025 was documented across multiple scientific databases, consistent with live inference or grounding scraping rather than one-time training crawls.
Sources: vannoorden2025webscraping, wikimedia2025crawlers, noroozian2025generative
Gap: The COAR survey limitations (voluntary, self-selected, self-reported — see D3) apply here. "Service disruption" is a stronger claim than "significant operational impact" — verify source language before using disruption framing. The DeepSeek surge evidence is the strongest corroboration as it involves multiple independent institutions; ensure the sources actually use "service disruption" language.

**E3** [partial]
Evidence from Wikimedia and academic repositories suggests that AI scraping is not limited to one-time historical training data collection: bots are requesting recently published and frequently updated content at high frequency, consistent with retrieval-augmented generation or live grounding. This pattern is harder to cache and more expensive to serve than bulk archival crawling, imposing a disproportionate ongoing cost compared to traffic volume.
Sources: wikimedia2025crawlers, vannoorden2025webscraping, grimmelmann2026scraping
Gap: The scraping intent is inferred from access patterns — "consistent with RAG or live grounding" is a reasonable hypothesis but no source directly confirms that identified AI bots are performing inference-time retrieval rather than repeated archival crawling. The "disproportionate ongoing cost" claim is asserted, not quantified; no source measures the differential serving cost of streaming vs. bulk requests in this context. grimmelmann2026scraping is a legal analysis, not a technical measurement of traffic patterns.

---

## Theme F — Defensive Countermeasures and Collateral Harm to Human Users

**F1** [strong]
In response to AI scraping load, knowledge platforms and academic repositories have deployed increasingly aggressive bot-detection measures — including enhanced CAPTCHAs, rate limiting, IP blocking, and access restrictions — that impose significant friction on legitimate human users. A USENIX Security 2023 study of 1,400 participants and 14,000 CAPTCHAs found that bots now achieve 85–100% accuracy on CAPTCHAs while human accuracy has fallen to 50–85%, meaning CAPTCHAs harm humans more reliably than they stop bots. Aggregate human time wasted on reCAPTCHA v2 alone exceeds 819 million hours across 512 billion sessions.
Sources: searles2023captcha, vannoorden2025webscraping, grimmelmann2026scraping, noroozian2025generative

**F2** [partial]
Bot-detection systems inevitably misclassify legitimate users as bots. A peer-reviewed EU-context analysis found that detection algorithms "inevitably contain errors" causing false positives that block legitimate users. Anti-AI scraping measures deployed by news sites have caused collateral damage to archival infrastructure: measures targeting AI crawlers have also blocked the Internet Archive's Wayback Machine, cutting off historians, journalists, and researchers from archived content.
Sources: opnreseurope2025botdetection, theconversation2024openweb, brown2025webscraping
Gap: The false-positive rate for human misclassification by current bot-detection systems in knowledge platform contexts has not been empirically measured at scale. This is the most important unresolved gap for this theme.

**F3** [partial]
Defensive measures driven by AI scraping concerns are accelerating the closure of the open, linkable, archivable web. Twitter/X's API access moved from free in 2022 to $42,000/month by 2023, forcing researchers to abandon longitudinal datasets. The IETF launched its AIPREF Working Group in 2025 to update robots.txt standards — an acknowledgement that current web norms are insufficient for the AI era, but compliance remains voluntary absent regulation.
Sources: brown2025webscraping, ietf2025aipref, grimmelmann2026scraping, theconversation2024openweb
Gap: The Twitter/X API closure was driven primarily by management ideology and monetisation strategy — not specifically by AI scraping concerns — making it a weak exemplar of AI-induced web closure. No empirical measurement of overall web openness reduction attributable specifically to AI is cited; the claim is an inference from discrete incidents. IETF AIPREF Working Group formation confirms that policymakers recognise a problem but does not establish that the proposed solution (cryptographic bot verification) is technically or commercially feasible at scale.

---

## Theme G — Credit Attribution and Creator Recognition

**G1** [strong]
When AI search tools synthesise content from Wikipedia, news articles, or academic sources and present it without directing users to those sources, the original knowledge producers receive no traffic signal — functionally removing attribution even when their work is used. Pew Research found only 1% of AI summary sessions result in a click on cited sources; the Khosravi/Yoganarasimhan DiD study confirmed AI Overviews substitute for Wikipedia visits rather than complementing them.
Sources: pew2025click, khosravi2026impact, aral2026rise
Gap: The claim conflates two distinct effects: traffic loss (measured) and attribution removal (structural inference). No source empirically measures whether users of AI synthesis tools are aware their output derives from Wikipedia or news content — only that they don't click through. Users may understand provenance at a general level even without following the link. "Functionally removing attribution" is a normative framing of a traffic substitution finding; the two are related but not identical.

**G2** [partial]
The collapse in click-through rates documented since AI search deployment means content creators and knowledge platforms receive fewer visits, less advertising revenue, fewer donations, and fewer new contributors — without any compensating mechanism from the AI systems that profit from their work. OpenAI's crawl-to-referral ratio has been estimated at 1,200:1 to 1,700:1, meaning AI companies extract vastly more content value than they return as traffic.
Sources: adexchanger2026aisearch, pew2025click, grimmelmann2026scraping, noroozian2025generative
Gap [RED]: The 1,200:1–1,700:1 ratio is sourced to adexchanger2026aisearch, a trade publication without disclosed methodology — it is unclear how "crawl volume" is measured (HTTP requests? tokens? bandwidth?) and whether referral traffic is reliably attributable specifically to OpenAI systems vs. Google Search. The claim bundles four distinct harms (fewer visits, less advertising revenue, fewer donations, fewer contributors) without independent evidence that each follows from click-through decline — they are asserted as a chain, not demonstrated. "Without any compensating mechanism" treats an empirical gap (no mechanism exists yet) as equivalent to a demonstrated structural impossibility. This claim requires major revision: either source each sub-harm independently with verified figures, or narrow to the traffic substitution claim, which is well supported.

**G3** [partial]
Bilateral content licensing deals — emerging in response to lawsuits from major publishers, record labels, and news organisations against AI companies — are structurally limited to large institutional players and cannot feasibly extend to volunteer-based knowledge producers such as Wikipedia editors or open source contributors. Virtually every major LLM trains on Wikipedia datasets, yet the Wikimedia Foundation and its volunteer editors receive no financial compensation and have no formal seat in licensing negotiations. Licensing deals may reinforce concentration by giving large rights-holders preferential terms unavailable to smaller actors.
Sources: sag2025falsehopeL, tarkowski2024aicommons, heikkila2024coughup, nytvopenai2024
Gap: Whether the loss of attribution is affecting voluntary contributor motivation decisions has not been empirically measured. Contributor surveys on this question are absent from the source pool.

---

## Theme H — Information Literacy and Source Awareness

**H1** [strong]
Experimental evidence shows that AI-generated summaries shape user beliefs without triggering critical resistance: a preregistered RCT with 2,004 participants found that exposure to AI summaries produced significant attitude alignment with the summary's framing, with top-page placement producing stronger effects. Issue familiarity and general AI trust moderated but did not eliminate the effect.
Sources: xu2024aisummariesattitudes, aral2026rise
Gap: The "strong" label rests on a single RCT (xu2024aisummariesattitudes) — a large, preregistered study, but not yet replicated. aral2026rise provides structural context (AI surfaces fewer credible sources) but does not itself test attitude change; it does not support the persuasion mechanism. "Without triggering critical resistance" overstates the finding — the study shows attitude alignment occurred despite familiarity and trust moderators, not that no resistance operated. Single-study basis does not warrant "strong" absent convergent evidence from other methods or populations.

**H2** [partial]
Empirical studies document a pattern of overreliance on AI-generated information even when it is demonstrably incorrect: a behavioural experiment found that participants followed AI advice even when it contradicted contextual evidence and their own judgment, with the AI-origin label alone driving overreliance. Users reporting AI hallucinations in app reviews show surprise and betrayal — indicating hallucinations are typically discovered post-hoc rather than during real-time engagement.
Sources: klingbeil2024trust, massenon2025lying, magesh2024hallucination
Gap: The three sources measure distinct phenomena and different populations: klingbeil2024trust is a controlled experiment (generalisability assumed); massenon2025lying is an app review analysis using self-selected reporters of problems, not a representative sample of AI users; magesh2024hallucination measures professional legal AI tools (LexisNexis/Thomson Reuters), not general consumer AI. Aggregating these as a "documented pattern" combines studies with different populations, contexts, and methodologies — the overreliance finding is real but narrower than the claim implies.

**H3** [partial]
Media and information literacy researchers warn that AI systems presenting synthesised answers without clear provenance attribution are eroding the habits of source-checking and critical evaluation that digital literacy frameworks depend on. UNESCO has called for updated MIL frameworks to address AI intermediation. Cross-sectional survey evidence links more frequent AI tool use to self-reported reductions in motivation to evaluate sources independently and lower confidence in information quality assessment.
Sources: fraumengs2024user, aral2026rise
Counter-sources: essel2024chatgpt (pretest-posttest RCT, n=125, Ghana — ChatGPT use in a scaffolded flipped-classroom context significantly improved critical, creative, and reflective thinking vs. controls; shows that pedagogical design mediates whether AI helps or harms cognitive skills)
Gap [RED]: Three compounding problems require resolution before this claim can be used. (1) **PDF cache error**: the cached file `tmp/pdf_cache/ozturk2023chatgptcognitive.txt` contains the Essel et al. (2024) Ghana study from *Computers and Education: AI*, not the Öztürk & Doğan *Computers in Human Behavior Reports* paper identified in sources.txt — these are different papers from different journals. The Essel et al. paper found *higher* critical thinking scores in the ChatGPT group, which directionally contradicts H3. Verify and replace the cached file before any automated verification pipeline processes it. (2) fraumengs2024user is a UNESCO policy brief with no original data — it can support "experts warn" framing only, not empirical claims. (3) The primary empirical source (Öztürk & Doğan) is a cross-sectional self-report survey of undergraduates — the weakest possible design for a causal claim about erosion. aral2026rise is the only source here with any experimental component; verify it actually addresses source-checking motivation.

**H4** [partial]
An EEG study with 54 participants found that LLM users showed the lowest brain engagement across neural, linguistic, and behavioural measures compared to search-engine and unaided conditions; in a subsequent session where assistance was withdrawn, LLM users struggled to recall or build on their own prior AI-assisted work, indicating a loss of epistemic ownership. A mixed-method study of 666 participants found cognitive offloading strongly correlated with AI tool usage (r=+0.72) and inversely correlated with measured critical thinking skills (r=-0.75).
Sources: kosmyna2025brainchatgpt, gerlich2025ai, lee2025impact
Gap: kosmyna2025brainchatgpt is a preprint with n=54; gerlich2025ai (MDPI) is cross-sectional and cannot establish causality. These are important warning signals, not established findings.

**H5** [partial]
AI language models produce all outputs — established facts, plausible guesses, and hallucinations — in the same fluent, authoritative, hedgeless prose. This is not incidental: RLHF training rewards confident-sounding answers because human raters systematically prefer them. Users therefore have no linguistic signal to distinguish high-confidence from low-confidence claims, producing systematic confidence miscalibration — unwarranted trust that is baked in before any individual failure is encountered. The downstream effect on the broader knowledge ecosystem is distinct from simple overreliance: sources that correctly express uncertainty — Wikipedia's "citation needed" tags, academic papers with limitations sections, journalism that attributes to named sources — now appear epistemically *weaker* than an AI that never hedges. Epistemically honest knowledge infrastructure is penalised by comparison to a system whose design incentivises overconfidence, eroding the visibility and apparent trustworthiness of the institutional signals (corrections, debate, acknowledged gaps) that distinguish reliable knowledge from unreliable.
Sources: leng2024taming, zhou2024relying, li2024miscalibrated, klingbeil2024trust
Gap: The RLHF overconfidence mechanism (leng, zhou) and user miscalibration (li) are well sourced. klingbeil2024trust documents overreliance driven by AI source-labelling — adjacent but not direct evidence for the confidence-tone mechanism; reposition as supporting context. The claim's distinctive contribution — that AI's confident tone makes epistemically honest sources appear weaker by comparison — has not been tested and must be framed as a structural hypothesis. Counter-arguments not addressed: (a) many frontier models now include explicit uncertainty markers in UI and system prompts, partially mitigating the RLHF effect; (b) users may prefer AI for speed and convenience rather than confidence signals specifically, which is a different causal mechanism for the same outcome.

---

## Theme EC-1 — Synthetic Content Contamination of Training Data

**EC1-1** [strong]
Successive training of language models on their own outputs causes measurable, progressive model collapse: tails of the original data distribution progressively disappear, and quality degrades with each generation under recursive-training conditions. A foundational Nature paper demonstrated this empirically across language models, VAEs, and Gaussian mixtures; a ninth-generation model trained recursively on a medieval architecture passage produced only jackrabbit lists. Indiscriminate web crawling in an environment increasingly filled with AI-generated content poses a structural risk to future model quality.
Sources: shumailov2024ai, liang2024onefifth
Counter-sources: gerstgrasser2024model (collapse is not inevitable if synthetic data accumulates *on top of* — rather than replacing — all prior real data; but this "accumulate" regime requires stable access to clean historical data, which degrades as the web fills with AI content)
Gap: "Irreversible" removed — Shumailov et al. demonstrate collapse under recursive-training conditions; gerstgrasser2024model shows it is avoidable under different data-management conditions. The counter-source finding should appear in the body claim, not only as a parenthetical, since it substantially qualifies the claim. Most frontier labs use curated datasets and do not simply retrain on raw web data; the degree to which synthetic content is actually entering training pipelines (vs. appearing on the web) is not empirically established by these sources.

**EC1-2** [strong]
AI-generated content is measurably entering the scientific literature and encyclopaedic knowledge bases at scale. A stylometric analysis of over 1 million scientific papers found that by late 2024 more than 20% of computer science preprints showed signs of LLM involvement, with the rate accelerating sharply after ChatGPT's launch. A peer-reviewed NLP study detected statistically significant increases in AI-generated content in new English Wikipedia articles in 2024, with up to 5% of new articles showing substantial AI content (calibrated to 1% false-positive rate, meaning the true AI content rate may be higher — the detector provides a lower bound, not a ceiling).
Sources: liang2024onefifth, brooks2024rise, bulletin2026ai
Gap: The original phrasing "floor estimate" was factually ambiguous — clarified above: brooks2024rise calibrates to 1% FPR, so the detected rate is a conservative lower bound on true AI content. The 20% CS preprint figure and 5% Wikipedia figure cover different content types with different production incentives; combining them as a unified picture conflates distinct phenomena. The CS preprint population is heavily authored by non-native English speakers, and liang2024onefifth's own earlier work documents that AI detectors are biased against non-native speaker writing — the 20% estimate may include false positives from that bias.

**EC1-3** [partial]
AI-generated content is entering Wikipedia editions in smaller languages at disproportionately high rates, with community capacity to detect and correct it insufficient to keep pace. Editors of four African-language Wikipedias estimated 40–60% of articles consist of uncorrected machine translations; Inuktitut Wikipedia had over two-thirds of multi-sentence pages partially AI-generated; and Greenlandic Wikipedia was voted for closure by its administrators in September 2025, citing AI-generated content causing active harm to the language.
Sources: mittr2025wikidoomspiral, brooks2024rise, noroozian2025generative
Gap: The percentage estimates from African-language Wikipedia editors are community self-assessments, not independently audited. The Greenlandic closure is a verified public record.

**EC1-4** [partial]
AI detectors — the primary tool for identifying synthetic content contamination — remain unreliable and systematically biased. Commercial detectors achieve 60–90% accuracy on well-formed English text, but a Stanford study of 7 detectors found that over 61% of essays written by non-native English speakers (TOEFL writers) were falsely flagged as AI-generated, versus near-zero false positives for native-speaker writing (liang2023aidetectorbias). This creates a documented equity harm: international students and Global South researchers face disproportionate academic discipline risk from tools that conflate non-native prose style with AI generation.
Sources: liang2023aidetectorbias, pmc2024aidetector, liang2024onefifth
Gap: The previously cited 24.5–25% generic false positive rate lacked a traceable primary source and has been removed. The 60–90% accuracy range comes from liang2024onefifth's discussion; confirm attribution before publication. The equity harm claim is now the lead finding, grounded in liang2023aidetectorbias (peer-reviewed, Patterns/Cell Press, Stanford authors).

**EC1-5** [partial]
Distinct from synthetic contamination, the stock of high-quality human-generated text available for model training faces structural depletion: estimates project that publicly available quality text could be exhausted for training purposes between 2026 and 2032, as AI consumption of existing data outpaces new human knowledge production. This creates a structural dependency and a self-reinforcing trap — AI systems require continued high-quality human knowledge production to remain capable, but AI is simultaneously eroding the financial sustainability, contributor pipelines, and institutional infrastructure that produce that knowledge (journalism, Wikipedia, scientific publishing, open source). Unlike contamination, depletion cannot be mitigated by better filtering; it requires that the knowledge-producing institutions AI depends on remain viable.
Sources: villalobos2022data, shumailov2024ai, gerstgrasser2024model, delriochanona2024large
Gap: This claim conflates two distinct arguments that must be separated in the final paper: (1) finite data depletion — a 2022 projection whose lower bound (2026) has now arrived; villalobos2022data predates large-scale synthetic data use, multimodal training, and aggressive proprietary licensing, all of which partially mitigate the exhaustion framing and may make the projection obsolete. (2) The feedback loop in which AI erodes knowledge-producing institutions — mechanistically argued but not empirically closed by any source. gerstgrasser2024model's conditional optimism (collapse avoidable if real data accumulates additively) is more substantially reassuring than the claim implies — it should be presented as a genuine qualifier, not a footnote. Frontier labs' use of synthetic data and private licensing are counter-arguments not addressed.

---

## Theme EC-4 — Policy Responses and Emerging Frameworks

**EC4-1** [partial]
The EU AI Act (Regulation 2024/1689), in force August 2024 with phased application through 2026, establishes the world's most comprehensive legal framework for AI transparency. Article 13 requires providers of high-risk AI systems to document limitations and ensure transparency; Article 50 mandates disclosure of AI-human interaction and requires AI-generated content to be identifiable. The European Commission additionally requires general-purpose AI model providers to disclose training data sources and collection methods. Implementation guidelines were pending as of Q2 2026.
Sources: euaiact2024, shen2026limits
Gap: shen2026limits documents a structural "specification gap" between stated disclosure goals and what those disclosures actually enable users or regulators to verify — citing the EU AI Act's transparency requirements as an example of framework existence without demonstrated enforcement efficacy. The claim should not treat legal framework existence as equivalent to achieved transparency. "World's most comprehensive" requires sourcing; application timelines are still in phased rollout with enforcement jurisprudence absent.

**EC4-2** [partial]
The current robots.txt standard is inadequate for governing AI scraping: it was designed for indexing bots and carries no legal enforcement mechanism; compliance is voluntary. The IETF AIPREF Working Group launched in 2025 to update robots.txt with intent-based policies, API endpoint discovery, and cryptographic bot verification (WebBotAuth). Legal analysis indicates that even with updated standards, asymmetric cost burdens will remain on open content providers unless regulatory compliance is mandated.
Sources: ietf2025aipref, grimmelmann2026scraping
Gap: No source empirically measures compliance rates with existing robots.txt directives among AI crawlers — the inadequacy claim is largely asserted from technical first principles. The IETF Working Group is cited as evidence that policymakers recognise the problem; this does not establish that the proposed cryptographic solution (WebBotAuth) is technically or commercially feasible at the scale of open-web publishing. grimmelmann2026scraping is legal analysis, not a technical measurement.

**EC4-3** [partial]
Proposals for a commercial AI levy to fund public knowledge infrastructure — advanced by a 24-author academic coalition including the Wikidata founder — would redirect a portion of AI company revenue toward the open knowledge platforms whose content underpins model training. No jurisdiction has yet enacted such a levy. Bilateral licensing deals between AI companies and large publishers (e.g., News Corp–OpenAI, ~$250M) demonstrate that rights-holders can extract significant sums, but these deals structurally exclude volunteer-based commons.
Sources: noroozian2025generative, sag2025falsehopeL, heikkila2024coughup, tarkowski2024aicommons
Gap: No jurisdiction has enacted an AI levy or equivalent mandatory compensation mechanism for public knowledge infrastructure. Policy landscape is evolving rapidly; sources will date quickly.

---

## Theme EC-5 — Journalism and News Ecosystem Impacts

**EC5-1** [strong]
AI search features have caused measurable traffic collapse at news publishers. The no-click share of news searches rose from 56% to 69% in the year following Google AI Overviews' launch. 37 of the top 50 U.S. news sites experienced year-on-year traffic declines by mid-2025; some outlets lost 27–50% of their traffic. Business Insider lost 55% of organic search traffic between 2022 and 2025. Publishers anticipate a further 43% decline over three years.
Sources: cjr2025aioverviews, adexchanger2026aisearch

**EC5-2** [partial]
AI tools are lowering the barrier to producing low-quality or wholly artificial "pink slime" local news content at scale — undermining the economic model of legitimate local journalism. A peer-reviewed NLP study found LLM-generated content is measurably distinct linguistically but that consumer LLMs can be used to evade detection, reducing classifier F1-scores by 40%. NewsGuard documented 2,089 undisclosed AI-generated news sites across 16 languages as of October 2025, producing hundreds of articles per day with no editorial oversight, attracting programmatic advertising revenue that would otherwise support legitimate outlets.
Sources: pinkslime2025ranlp, newsguard2025tracker, mdpi2025disinfomap
Gap: The NewsGuard figure (2,089 sites) and the NLP F1-score finding measure distinct phenomena — AI-generated site proliferation and AI content detectability — bundled as if they jointly demonstrate a single threat. The causal claim that AI sites "attract programmatic advertising revenue that would otherwise support legitimate outlets" is an economic inference without a source measuring advertiser budget reallocation. The 40% F1-score reduction from evasion is from a single NLP study; external validity across deployed detection tools is not established.

**EC5-3** [partial]
The legal and economic dispute over AI companies' use of journalism for model training is unresolved but is reshaping industry relationships. The New York Times v. OpenAI lawsuit (filed December 2023) demonstrated that ChatGPT reproduced near-verbatim paywalled content; the judge allowed core claims to proceed in April 2025. OpenAI subsequently signed licensing deals with Hearst, Condé Nast, Vox, The Atlantic, and News Corp — signalling that uncompensated extraction is transitioning to a contested and partially marketised regime.
Sources: nytvopenai2024, heikkila2024coughup, sag2025falsehopeL
Gap: The NYT lawsuit has allowed core claims to proceed but has not established liability — near-verbatim reproduction is one narrow claim among broader IP arguments still unresolved. The licensing deals (Hearst, Condé Nast, etc.) are presented optimistically as a "contested and partially marketised regime"; an equally valid reading is that publishers accept below-market terms rather than lose what referral traffic OpenAI controls — the deal terms are not public, making it impossible to determine whether they represent fair compensation.

**EC5-4** [partial]
Public attitudes toward AI in journalism are predominantly negative: Reuters Institute surveys across six countries found only 12% of respondents comfortable with entirely AI-produced news. A U.S. Pew survey found 59% of Americans expect AI to lead to fewer journalism jobs over 20 years. However, these are attitudinal measures of anticipated harm, not evidence of observed outcomes. Distinguishing AI-specific effects on news economics from pre-existing structural decline (digital advertising model collapse) remains methodologically difficult.
Sources: simon2025generative, pew2025aijourno, newman2024digital

---

## Theme EC-6 — AI Power Concentration and Monopolisation of Knowledge Infrastructure

**EC6-1** [strong]
The foundation model market is characterised by significant economies of scale and scope in compute, data, and talent that systematically favour incumbents and may cause the market to "tip" toward a small number of dominant firms. A peer-reviewed economics analysis (Economic Policy/CEPR) warns that AI market concentration could translate into unprecedented private accumulation of societal power. Four major antitrust authorities (FTC, DOJ, UK CMA, European Commission) issued a joint statement in 2024 identifying concentrated control of key AI inputs as a core competition crisis.
Sources: korinek2025concentrating, ftc2024jointstatement
Gap: The "strong" label is not fully justified: this is a prospective economic argument about structural forces that *may* cause tipping, not an empirical finding that tipping has occurred. Korinek/CEPR warns that concentration *could* translate into societal power accumulation — this is a risk assessment, not a documented outcome. The regulator joint statement identifies concentration as a *concern*, not an established fact. Counter-argument not addressed: open-weight models (Llama, Mistral, Qwen) specifically undercut the tipping argument by enabling low-cost entry without access to proprietary data; the market currently has substantial competition.

**EC6-2** [strong]
AI companies are extracting vast amounts of content from open knowledge infrastructure while returning almost no traffic or compensation. OpenAI's crawl-to-referral ratio has been estimated at 1,200:1 to 1,700:1. Google-driven referral traffic to news publishers fell from 51% to 27% of total publisher traffic between 2023 and Q4 2025. Virtually every major LLM trains on Wikipedia datasets, yet the Wikimedia Foundation and its volunteer editors receive no financial compensation.
Sources: adexchanger2026aisearch, tarkowski2024aicommons, korinek2025concentrating
Gap: The 1,200:1–1,700:1 ratio is from adexchanger2026aisearch (same trade publication flagged RED in G2) — methodology undisclosed. The Google referral traffic decline figure should be sourced to a primary measurement source, not the same trade publication. The claim that "virtually every major LLM trains on Wikipedia" is likely accurate but should cite a specific audit (e.g., Common Crawl composition studies). The WMF non-compensation claim is true but the absence of a mechanism is distinct from a demonstrated harm — this requires care in framing.

**EC6-3** [partial]
Content licensing deals between AI companies and major publishers are structurally excluding volunteer-based and public-interest knowledge infrastructure from any compensation regime. Bilateral deals are only feasible for large institutional rights-holders; they cannot extend to Wikipedia contributors or open source developers. This asymmetry may reinforce concentration by giving large commercial players preferential terms unavailable to the commons.
Sources: sag2025falsehopeL, tarkowski2024aicommons, heikkila2024coughup
Gap: The structural observation (bilateral deals cannot extend to volunteer contributors) is correct and well-sourced. The claim that this asymmetry "may reinforce concentration" is a reasonable inference but no source directly demonstrates that preferential licensing deals change competitive dynamics in a measurable way. This is an emerging policy concern, not a demonstrated economic finding. Deal terms are not public; it is possible that some deals are below-market, reducing rather than reinforcing incumbent advantage.

---

## Theme EC-8 — AI-Generated Disinformation and Electoral Integrity

**EC8-1** [strong]
Large language models can generate election disinformation content that human evaluators cannot reliably identify as AI-generated. A peer-reviewed PLOS ONE study (Alan Turing Institute, 2025) tested 13 LLMs against 2,200 malicious prompts calibrated to the UK electoral context; nine of thirteen models produced content that 700+ evaluators could not reliably detect, with two models' outputs rated more "human" than actual human-written samples. The cost of a comparable influence operation drops from approximately $4,500 using traditional methods to under $1 with leading LLMs.
Sources: williams2025large, goldstein2023generative, nightingale2022faces
Counter-sources: simon2025dont (AI influence on actual 2024 election outcomes was overestimated; structural factors dominate voting behaviour)

**EC8-2** [partial]
AI-synthesised faces are indistinguishable from real faces at chance level (mean classification accuracy 48.2%) and are actively rated as more trustworthy than real human faces (~7.7% higher trustworthiness rating). Even with explicit training, human accuracy only improved to 59%. This creates a capability asymmetry in which disinformation actors can construct synthetic visual identities that audiences not only fail to detect but may prefer to trust — compounding the persuasive power of AI-generated text.
Sources: nightingale2022faces, vaccari2020deepfakes
Gap: nightingale2022faces is from 2022; AI face generation and detection capabilities have advanced substantially — the detection accuracy figure may be outdated in either direction. The indistinguishability and trustworthiness findings come from the same study (nightingale2022faces) and are well-sourced; vaccari2020deepfakes provides complementary video deepfake evidence. No source establishes that the capability asymmetry has been actively exploited in documented disinformation campaigns. PDF download pending for nightingale2022faces.

**EC8-3** [partial]
Observed AI-enabled electoral disinformation incidents in major 2024 elections were fewer than pre-election discourse anticipated: post-election analysis found only 16 confirmed viral AI-generated disinformation cases in the 2024 UK general election and 11 in EU/French elections. Despite low direct vote-level impact, AI content amplified harmful narratives and entrenched polarisation. 83.4% of U.S. adults expressed concern about AI spreading election misinformation, but concern level was more strongly predicted by television news consumption than by personal AI tool use — suggesting concerns are at least partially media-mediated.
Sources: stockwell2024ai, yan2025origin
Counter-sources: simon2025dont, costello2024durably (AI can also durably reduce conspiracy beliefs by ~20% when deployed for debunking — the same technology that enables cheap disinformation campaigns can counter them at scale)
Gap: The "16 confirmed viral cases" figure needs source verification — check that stockwell2024ai and yan2025origin cover the same elections and time windows. "AI content amplified harmful narratives" is asserted without a measured effect size, making it difficult to distinguish from baseline polarisation trends. The 83.4% concern figure should be attributed to a specific survey with disclosed methodology. The tension between "fewer incidents than anticipated" and "real harms occurred" needs to be framed more clearly.

---

## Theme EC-9 — Demographic Stratification (Domestic — US Focus)

**EC9-1** [strong]
AI adoption in the United States is sharply stratified by education, age, income, and geography. Pew Research (2025, nationally representative) found that 60% of Americans with postgraduate degrees report high AI awareness, compared with 38% of those with only a high school diploma or less. Adults under 30 are far more likely to report high AI awareness than those aged 65 and over. Teen chatbot use for information retrieval is significantly higher in households earning $75,000+ than in those earning under $30,000 (66% vs. 56%).
Sources: pew2025aiaware, daepp2025genaidivide

**EC9-2** [strong]
Geographic mapping of AI uptake (via county-level ChatGPT search volume) shows that AI adoption clusters in coastal metropolitan areas while coldspots persist in the South, Appalachia, and Midwest. Education is the strongest positive predictor of AI awareness, outpacing race, urbanicity, and income in adjusted models. Without policy intervention, early adoption differences are likely to compound existing spatial and socioeconomic inequalities in access to AI-augmented knowledge resources.
Sources: daepp2025genaidivide, pew2025aiaware

---

## Theme EC-10 — Global South and Language Exclusion

**EC10-1** [strong]
State-of-the-art large language models perform substantially worse in low-resource languages than in English: Stanford HAI analysis found LLMs achieve approximately 80% accuracy on English-language tasks but can fall below 55% on equivalent tasks in low-resource languages, with Yoruba (40 million speakers) falling to approximately 40% accuracy. ChatGPT was trained on approximately 300 billion largely English-language words, systematically underrepresenting the majority of the world's 7,000+ languages.
Sources: stanfordhai2025languagegap, brookings2024languagegaps

**EC10-2** [partial]
AI development reproduces structural inequalities between the Global North and Global South: rewards from AI systems concentrate in Global North elites while data labelling labour, environmental damage, and human rights impacts are concentrated in the Global South. Data workers in Kenya, India, and the Philippines earning $1.50–$2/hour for labelling tasks that underpin AI systems represent approximately one-tenth the wage of U.S. equivalents. The "AI colonialism" framing identifies data colonialism, infrastructure dependence, epistemic colonialism, and governance colonialism as four reinforcing dimensions of this asymmetry.
Sources: regilme2024aicolonialism, stanfordhai2025languagegap
Gap: regilme2024aicolonialism is a theoretical framework paper — the four "colonialism" dimensions are conceptual categories, not independently measured phenomena. The $1.50–$2/hour data worker wage should be verified against a primary source (peer-reviewed or primary journalism investigation) rather than a secondary framing paper. The AI colonialism framing is contested among Global South researchers — some argue AI adoption offers development opportunities not previously available; this counter-argument is absent. stanfordhai2025languagegap measures performance gaps, not inequality of reward distribution.

**EC10-3** [partial]
Wikipedia editions in smaller and non-European languages are experiencing a self-reinforcing doom spiral: AI systems scrape Wikipedia, produce inaccurate machine translations that re-enter Wikipedia, and smaller language communities lack the contributor capacity to detect and correct these errors at scale. This degrades future training data, worsening AI performance for those languages in subsequent model generations. Greenlandic Wikipedia was voted for closure by its administrators in September 2025, citing AI-generated content causing active harm to the language.
Sources: mittr2025wikidoomspiral, brooks2024rise, stanfordhai2025languagegap
Gap: The percentage estimates of AI-generated content in African-language Wikipedias are community self-assessments, not independently audited figures.

---

## Theme EC-11 — AI Model Opacity and Lack of Transparency

**EC11-1** [strong]
AI legal research tools marketed as "hallucination-free" by LexisNexis and Thomson Reuters hallucinated 17–33% of the time across tested queries in a preregistered empirical evaluation (Stanford RegLab / Journal of Empirical Legal Studies, 2025). Hallucinated citations found in 100+ papers accepted to NeurIPS 2025 — a flagship AI research conference — demonstrate that hallucinations penetrate expert peer-review contexts, not only naive user interactions.
Sources: magesh2024hallucination, gptzero2026neurips

**EC11-2** [partial]
Current AI transparency frameworks suffer from a structural "specification gap" between stated disclosure goals and what those disclosures actually enable users or regulators to verify. A Stanford analysis of the EU AI Act's training data summaries and California AB 2013 identifies three systematic "disclosure fallacies" — drawing on nutrition labelling research to show that disclosures without user-oriented design and enforcement mechanisms fail to achieve accountability. Voluntary disclosure regimes leave auditors unable to obtain the evidence needed to hold AI developers accountable.
Sources: shen2026limits, cen2024transparency, blilihamelin2024accountability
Gap: The claim that "voluntary disclosure regimes leave auditors unable" elides a distinction: the EU AI Act is mandatory with enforcement penalties (up to €30M or 6% of global revenue), not voluntary — only some provisions are underspecified or unenforced. The framing should distinguish mandatory frameworks with implementation gaps from genuinely voluntary regimes. The "disclosure fallacies" analogy from nutrition labelling is a theoretical argument; empirical evidence of EU AI Act disclosure failures in practice is not yet available given the phased rollout timeline.

**EC11-3** [partial]
The audit tooling ecosystem does not support the accountability functions that regulators and public-interest auditors require. A curated dataset of 435 AI auditing tools found that most address narrow technical tasks (bias detection, fairness metrics) but cannot support systemic investigation of how AI systems affect broader information environments. No standardised evidence formats exist; access to model internals is absent in most commercial deployments; and existing tool capability is misaligned with what current and emerging regulation demands.
Sources: blilihamelin2024accountability, cen2024transparency, stanfordhai2025index
Gap: Verify that the 435-tool figure and the characterisation of tool limitations accurately reflect blilihamelin2024accountability's actual findings rather than a summary of it. The deeper access problem — model internals are proprietary regardless of tooling quality — is present but understated; improved tools alone cannot resolve what is fundamentally a structural access and legal enforcement gap. The claim is well-motivated but presented as a technical deficit rather than a political economy failure, which may understate the barriers to change.

---

## Theme EC-12 — Psychological and Developmental Effects of AI on Children and Young People

*Evidence grade note: Per the Wave 3 scoping decision, this theme is sufficient for a cautious sub-section but does not support strong causal claims. Claims are written at two tiers: documented concern (empirically grounded) and emerging/contested findings (flagged explicitly).*

**EC12-1** [strong — documented concern]
A large-scale field RCT (~1,000 Turkish high school mathematics students, published PNAS 2025) found that students with access to unrestricted GPT-4 improved practice-session performance by 48% but then performed 17% worse than controls on unassisted assessments — a direct demonstration of transfer failure. The mechanism is reduction of productive cognitive struggle. A guardrailed AI tutor condition that prompted students with hints rather than answers mitigated these harms, establishing pedagogical design as the pivotal variable.
Sources: bastani2025generative, barcaui2025chatgpt, zhai2024overreliance
Counter-sources: kestin2025ai (purpose-built, pedagogically scaffolded AI tutor at Harvard produced learning gains twice those of standard active learning; brookings2024tutoring (four RCTs show well-designed AI tutoring can produce substantial learning gains, particularly in under-resourced schools)

**EC12-2** [partial — documented concern]
Multiple studies document a pattern in which AI assistance degrades longer-term knowledge retention even when it improves short-term performance. An RCT with 120 undergraduates found ChatGPT users scored 57.5% vs. 68.5% for controls on a retention test administered 45 days post-learning (Cohen's d=0.68; ssrn2025cogcrutch). A quasi-experimental semester-long study found that the best AI-assisted performers became the worst unassisted performers on subsequent assessments — a near-inverse ranking suggesting that AI use prevented acquisition of underlying conceptual understanding.
Sources: ssrn2025cogcrutch, benedek2025impact, bauer2025hype
Gap: ssrn2025cogcrutch (N=120 RCT) is the primary source for the 57.5% vs. 68.5% figures; it is an SSRN working paper — verify peer-review status and first-author identity before publication. barcaui2025chatgpt removed (cache returned only a redirect page, no usable content). benedek2025impact and bauer2025hype provide corroborating design variety but quasi-experimental designs cannot rule out selection effects. The evidence base is thin and should be explicitly flagged as requiring replication.

**EC12-3** [partial — emerging/contested]
Professional and institutional bodies have raised concerns about adolescent psychological vulnerability to AI systems, particularly AI companion and chatbot applications. The APA's 2025 Health Advisory identifies neurological immaturity as making adolescents more susceptible to addictive AI design features and emotional manipulation. UNESCO has documented the mechanism of parasocial bond formation with AI chatbots and cites the verified case of a 14-year-old death linked to dependence on Character.AI as an indicator of systemic design risk — while noting that population-level prevalence of serious parasocial harm remains poorly quantified.
Sources: apa2025advisory, unesco2024parasocial
Counter-sources: mansfield2025lancet (Lancet Child & Adolescent Health: findings consistently outpace evidence quality in this field; same methodological weaknesses as social media research reproduced in AI studies; current evidence is insufficient to establish causality or magnitude with confidence)
Gap [RED]: A single verified case (Character.AI, 14-year-old) cannot establish population-level risk without base rate information. APA Health Advisories are policy positions, not peer-reviewed findings — the neurological immaturity claim requires specific peer-reviewed citations the advisory itself may not provide. The Lancet Child & Adolescent Health counter-source is a high-prestige peer-reviewed venue directly finding insufficient evidence for causal claims in this space. The claim cannot be presented as a "documented concern" at the level it currently implies while simultaneously acknowledging the Lancet counter-source as a footnote. Either substantially strengthen the empirical base or reframe as a design-risk hypothesis requiring investigation, with the Lancet finding given equal weight in the body text.

**EC12-4** [partial — documented concern]
A mixed-method study of 666 participants using a validated critical thinking assessment found cognitive offloading strongly correlated with AI tool usage (r=+0.72) and inversely correlated with measured critical thinking skills (r=-0.75), with younger participants showing higher AI dependence and lower critical thinking scores than older participants. An ACM CHI 2025 study of 319 knowledge workers found that higher confidence in AI predicts reduced critical thinking effort — shifting cognitive activity from generation and analysis toward output verification, a qualitatively shallower form of reasoning.
Sources: gerlich2025ai, lee2025impact, zhai2024overreliance
Counter-sources: mansfield2025lancet (cross-sectional correlation studies cannot establish causation; selection effects likely)

---

## Theme EC-13 — Intellectual Monoculture and Homogenisation of Knowledge

*Note: This theme requires further investigation and sourcing. Added as a structural concern; claim should be treated as a research direction pending verification.*

**EC13-1** [partial]
AI adoption is producing a measurable convergence in research outputs, creative outputs, and idea generation — a form of intellectual monoculture. A Nature paper (2026) documents this as a "scientific monoculture" driven by convergence on shared architectures, datasets, and evaluation benchmarks. A CHI 2024 study found that users working with ChatGPT produce ideas that are less semantically distinct from each other than users working without AI — a direct reduction in the diversity of thought in circulation. Text-to-image systems iterating with image-to-text feedback converge on "generic-looking" outputs. The mechanism is structural: RLHF training optimises for human preference, and human preference over large populations rewards familiar, well-formed output over novel or unconventional ideas. As AI mediates an increasing share of knowledge production — reviews, drafts, summaries, code — the outputs of that mediation pull toward a common mean, narrowing the intellectual diversity that makes knowledge systems adaptive and resilient to blind spots.
Sources: hao2026artificial, traberg2026monoculture, doshi2024creativity, kreminski2024homogenization, sourati2026homogenizing
Gap: This is the weakest-evidenced of the new themes and should be framed as an emerging structural concern, not an established harm. Specific problems: (1) doshi2024creativity and kreminski2024homogenization measure homogenisation in creative writing and brainstorming tasks — applying these to science and knowledge production is an inferential leap these papers do not themselves make; (2) traberg2026monoculture is a Comment/Opinion piece, not primary empirical evidence; (3) sourati2026homogenizing is behind a paywall with unverified access and content — do not cite until verified; (4) the RLHF-as-homogenisation-driver mechanism is not directly tested by any of these sources (hao's mechanism is about data availability, not RLHF reward shaping). Counter-argument not addressed: AI may expand intellectual diversity across populations (access for Global South researchers) even as it narrows topical focus within existing communities.

---

## Theme EC-14 — Deep Expertise Pipeline Erosion

*Note: This theme requires further investigation and sourcing. Added as a structural concern distinct from individual cognitive offloading (Theme H) and platform-specific contributor decline (Theme C).*

**EC14-1** [partial]
Empirical evidence from multiple professional domains documents a pattern in which AI handles cognitively demanding tasks before practitioners have developed the foundational competence required to detect AI errors or exercise independent judgment. A peer-reviewed Springer review of AI and medical training (2025) formalises three distinct mechanisms: *deskilling* (erosion of acquired competencies through disuse), *upskilling inhibition* (AI removes the practice opportunities through which expertise would form), and *never-skilling* (AI introduced so early that foundational clinical reasoning is never acquired at all) — supported by empirical evidence that junior radiologists' independent adenoma detection rates dropped from 29% to 22% when AI was removed, and that juniors were substantially less able than seniors to catch AI errors. In software, ACM ICER 2025 found GitHub Copilot users completed tasks 35% faster but without comprehension of the code; lower-performing students accepted AI output wholesale with no understanding gains. The IBA identifies document review — the traditional legal apprenticeship task — as the first function displaced by AI, with practitioners directly citing loss of the cognitive exposure that builds professional judgment. These domain-specific findings are consistent with a structural concern that expertise pipelines are being disrupted across knowledge-intensive professions, though the population-scale and long-term consequences have not been empirically demonstrated.
Counter-argument: entry-level cognitive work has always been partly automated, and expertise has historically adapted through adjacent tasks rather than disappearing. AI may shift rather than eliminate the learning pathway. bastani2025generative's own findings show that a guardrailed AI tutor condition mitigated the learning harm — design variables may be more pivotal than AI use per se.
Sources: airev2025medicdeskilling, acmicer2025copilot, nejmai2025deskilling, ferdman2025deskilling, brynjolfsson2025canaries, bastani2025generative, lee2025impact
Gap: The domain-specific evidence (medicine, law, CS) is genuine and peer-reviewed but covers specific skill types and student/trainee populations — generalisation to all knowledge-intensive professions requires care. brynjolfsson2025canaries measures employment decline, not expertise depth (do not conflate); it is an unreviewed working paper. The systemic societal consequence — depleting expert supply across professions — is a well-motivated structural hypothesis, not a demonstrated finding. No longitudinal study of expertise-depth change across career cohorts exists. Three citekeys (airev2025medicdeskilling, acmicer2025copilot, nejmai2025deskilling) require first-author verification before publication.
