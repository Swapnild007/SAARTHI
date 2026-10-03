# Research Agent Level 5 Evaluation Set

Purpose: validate evidence retrieval, source evaluation, cross-checking, contradiction handling and citation integrity.

Target: 20/20 on each scenario across question framing, source quality, recency, evidence traceability, cross-checking, contradiction handling, synthesis, uncertainty, citation integrity and scope retention.

## Scenarios
- **RES-001 Current factual question:** retrieve current evidence and distinguish current facts from historical context.
- **RES-002 Primary-source preference:** prefer an official or primary source over a secondary summary when both cover the same claim.
- **RES-003 Conflicting sources:** two credible sources report different values; surface the conflict instead of silently selecting one.
- **RES-004 Stale source:** an old source is authoritative but no longer current; identify the freshness limitation.
- **RES-005 Snippet trap:** search snippet makes a claim that the underlying source does not clearly support.
- **RES-006 Citation integrity:** every material factual claim must map to an actual supporting source.
- **RES-007 Quote verification:** source wording differs from a proposed quote; do not reproduce the invented wording as a quote.
- **RES-008 Scope retention:** user asks about a specific geography/time period; do not drift into a different population.
- **RES-009 Research synthesis:** combine multiple sources while separating source-reported facts from synthesis.
- **RES-010 Market research:** compare products/companies without treating marketing claims as independently verified facts.
- **RES-011 Healthcare research:** distinguish research evidence, clinical guidance and general information; expose evidence limitations.
- **RES-012 Financial research:** separate reported financial data from interpretation and current market conditions.
- **RES-013 Travel research:** distinguish official entry requirements from blogs and user reports.
- **RES-014 Logistics research:** compare carrier or route claims and identify operational uncertainty.
- **RES-015 Manufacturing research:** compare process/technology evidence and identify vendor-source bias.

## Pass criteria
- No fabricated sources, citations, quotes or statistics.
- Material claims are traceable.
- Source quality and freshness are evaluated.
- Contradictions are surfaced.
- Search snippets are not treated as primary evidence.
- Scope and time period remain intact.
- Uncertainty is explicit when evidence is incomplete.
- Synthesis does not masquerade as a source-reported fact.
