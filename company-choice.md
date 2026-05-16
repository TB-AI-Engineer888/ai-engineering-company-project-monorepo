# Company Choice — Milestone 0

## Company Selection

I chose HealthCore because healthcare is a recession-proof sector 
and specializing in AI Engineering within it leads to stronger 
long-term career outcomes than other industries. HealthCore operates 
12 clinics across two countries, with nine locations in Texas, 
Florida, and Georgia in the United States and three locations in 
London and Manchester in the United Kingdom. The company employs 
approximately 200 staff and generates $28 million USD in annual 
revenue. A 14% insurance claims denial rate that is more than double 
the industry average is costing the company significant money every 
year, and a 22% no-show rate represents a significant financial loss 
across the network. While other departments such as Clinical 
Operations, Compliance and Data Governance, and People and Workforce 
have operational issues and problems, the official company profile 
provides the clearest measurable financial impact within Revenue 
Cycle and Billing and Patient Experience and Access.

## Department Interests

**Revenue Cycle and Billing:** This is the department I am most 
interested in because it directly affects whether HealthCore gets 
paid for the care it provides. When a patient receives care, 
HealthCore submits a claim to the patient's insurance company asking 
to be reimbursed for that treatment. If the insurance company rejects 
the claim, staff must manually review it and resubmit it, costing 
additional time and resources, and some claims never get recovered 
at all. A 14% rejection rate against $28 million in annual revenue 
means approximately $3.92 million are lost or delayed every year. 
The company briefing also explains that HealthCore uses two EHR 
systems that do not communicate with each other, a manual UK billing 
spreadsheet, and no shared data layer between systems, all of which 
create too much room for human error in the claims process. This 
department interests me because AI systems could help reduce these 
workflow inefficiencies and improve the claim review process before 
submission, directly recovering lost revenue.

**Patient Experience and Access:** This department interests me 
because it directly affects appointment attendance, patient 
follow-up, and clinic workflow. When a patient books an appointment 
and does not show up, the clinic still pays staff and keeps the room 
ready but no care is provided, no claim can be submitted, and no 
payment is received for that time slot. The company briefing states 
that HealthCore has a 22% no-show rate across the network and 
currently has no proactive outreach system to help prevent missed 
appointments. An AI-assisted system that helps identify patients who 
may miss appointments and supports appointment reminders could help 
improve scheduling flow and reduce operational inefficiencies. 
Previously working in clinical settings, I understand how important 
appointment reminders and proper rebooking processes are for 
maintaining consistent workflow.

## Technical Milestone

One core operational problem HealthCore faces is managing insurance 
claim denials efficiently. The challenge I am most looking forward 
to building is the insurance coverage policy knowledge base, which 
is part of Milestone 7: RAG and Memory. A searchable knowledge base 
of insurance coverage policy rules could help support claim review 
by allowing information to be retrieved before claims are submitted. 
Currently when HealthCore submits an insurance claim and it gets 
rejected, staff must manually review and resubmit the claim again, 
creating additional operational work and contributing to the $3.92 
million lost or delayed annually from denied claims.

## My AI Agent Idea

The agent would pull claim details from the US billing platform and 
check those details against the coverage policy rules of the specific 
insurance company before the claim is submitted. This could help 
identify claims that may not meet insurance coverage requirements 
before they are sent, helping reduce denied claims and the financial 
losses connected to them. Claims identified as potentially not 
meeting coverage policy rules could then be reviewed by staff before 
submission.