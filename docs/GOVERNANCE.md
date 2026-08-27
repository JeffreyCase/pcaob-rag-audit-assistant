# Audit and AI Governance Notes

## Intended use

The prototype is intended to support education and preliminary research into selected public PCAOB inspection findings. It can help a user locate relevant passages and understand recurring audit issues.

It is not intended to:

- provide audit evidence or an audit conclusion;
- interpret standards authoritatively;
- rank firms or engagements;
- process confidential client information;
- replace supervision, review, or professional judgment; or
- operate as a production application without additional controls.

## Controls demonstrated in the prototype

- Use of public source documents only.
- Report-and-page metadata retained with each chunk.
- Prompt restricted to retrieved source excerpts.
- Exact refusal language for unsupported requests.
- Explicit prohibition on firm-quality rankings.
- Separate retrieval and generation evaluation.
- Automated checks followed by human review.
- API credential requested through an environment variable rather than stored in code.
- Gemini Interaction requests configured with `store=False`.

These measures reduce risk but do not establish production readiness or regulatory compliance.

## Future-state controls for a firm deployment

| Risk | Illustrative control |
|---|---|
| Confidential information enters a prompt | Approved-data policy, prompt sanitization, data-loss prevention, and user training |
| Unauthorized use | Firm authentication, role-based access, least privilege, and periodic access review |
| Unsupported or inaccurate output | Source display, evidence sufficiency rules, claim-level citation checks, and mandatory reviewer approval |
| Model or prompt changes alter behavior | Version control, change approval, regression testing, and release documentation |
| Provider retains or reuses data | Contractual review, approved enterprise configuration, retention controls, and vendor monitoring |
| Activity cannot be reconstructed | Firm-controlled audit logs that exclude or minimize sensitive prompt content |
| Corpus becomes stale or incomplete | Document inventory, effective-date tracking, scheduled updates, and completeness checks |
| Users over-rely on the tool | Visible limitations, training, escalation rules, and accountability assigned to the auditor and reviewer |

## Relevant professional principles

The AICPA General Standards Rule addresses competence, due professional care, planning and supervision, and sufficient relevant data. Applied to this prototype, those principles support independent evaluation of source excerpts and generated guidance. The Compliance With Standards Rule requires adherence to applicable standards; it does not specifically classify AI output as or as not constituting workpapers. The Confidential Client Information Rule and its third-party-provider interpretations are relevant if a firm sends client information to an external service.

COSO's GenAI materials adapt internal-control concepts to AI-related risks and emphasize disciplined oversight, clarity, traceability, monitoring, and control design. They are governance guidance, not a certification or legal determination that this prototype is compliant.

## Required user disclaimer

> This output is educational coaching based on selected public PCAOB inspection reports. It is not audit evidence, authoritative guidance, or a substitute for reviewing the original source, applicable professional standards, firm methodology, and the complete engagement facts. The auditor and reviewer remain responsible for all judgments and conclusions.

