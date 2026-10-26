"""Worked demonstrations, kept separate from the production prompt contracts."""

# ruff: noqa: E501
# Keep JSON string examples on single lines so the rendered examples remain valid JSON.

FRAMEWORKS = """WORKED NODE 0 EXAMPLE — demonstration k=5
Brief: 'Suggest a growth strategy for an independent bicycle repair shop.'
These are five possible framework contracts, not five finished strategies. Attribution
states the source and its kind of backing; local market claims still require evidence.

1. Access-led growth through Jobs to Be Done
   origin: adapted
   attribution: Clayton Christensen and collaborators; Jobs to Be Done, as described by the
     Christensen Institute. Conceptual/research-informed lens on progress in circumstances.
     Adaptation: focus on access barriers; add a local demand test, not a claimed JTBD recipe.
   principle: Understand the progress a customer seeks and what prevents switching to repair.
   required_components: [Access barrier, Repeatable access model, Delivery trade-off, Demand test]
   progression: Establish circumstances, desired progress and switching friction → design
     access → constrain delivery → test the job hypothesis with actual customers.
   completion: Access addresses functional/social/emotional progress; barriers and testable
     assumptions are explicit; no invented interviews or demand results.
2. Competitive positioning and activity fit
   origin: established
   attribution: Michael E. Porter, What Is Strategy? Conceptual competitive-strategy framework,
     not empirical proof that a proposed shop strategy will succeed.
   principle: Serve a distinct value proposition with reinforcing activities and real sacrifices.
   required_components: [Distinct value proposition, Different activities, Strategic trade-offs, Activity fit]
   progression: Choose whom/value → configure activities → exclude incompatible offers → check fit.
   completion: Activities reinforce the position; choices about what not to do are consequential.
3. Value-chain redesign
   origin: established
   attribution: Michael E. Porter, Competitive Advantage; value-chain analysis, a conceptual
     framework for examining activities and their links as sources of cost and differentiation.
   principle: Change the configuration of service activities to improve customer value or cost.
   required_components: [Activity map, Cost or differentiation drivers, Linked activity redesign, Economic assumptions]
   progression: Map activities → identify drivers → redesign linked work → examine economics.
   completion: Changes name affected activities and links; unknown costs remain assumptions.
4. Double Diamond for a service-growth opportunity
   origin: adapted
   attribution: Design Council, Double Diamond; practitioner design process. Adaptation:
     this generated plan proposes discovery and tests rather than pretending to conduct them.
   principle: Separate understanding the problem from developing and testing a service response.
   required_components: [Discovery questions, Defined challenge, Alternative service concept, Delivery test]
   progression: Discover → define → develop → deliver, with proposed iteration on test findings.
   completion: The concept addresses the defined challenge; learning and delivery risks can be tested.
5. Business-model coherence
   origin: adapted
   attribution: Clayton Christensen and collaborators, four-box business model framework
     described by the Christensen Institute; conceptual model. Adapted to one shop's growth.
   principle: Align the customer value proposition, profit formula, key resources and processes.
   required_components: [Customer value proposition, Profit formula, Key resources, Key processes]
   progression: Define value → propose revenue/cost logic → identify resources → align processes.
   completion: The four elements fit together; capacity and margin hypotheses are explicit.

Illustration: if Python selects index 0, the planner receives Access-led growth through Jobs to Be Done only.
No framework is the recommended winner. Real outputs also include origin, attribution,
organizing_principle, required_components, progression_rules and completion_criteria in the
declared schema; the compact labels above are just for readability.
"""

WORKFLOWS = """WORKED WORKFLOW EXAMPLES — demonstration k=5
Each table is one ordered list, executed from top to bottom. Each node generates k candidates;
Python selects one BEFORE the next node starts. Every normal node sees the brief, framework
and ALL earlier selected values. Only rows marked isolated_context=true receive cue/instructions
alone. Final writing happens after the list and produces the work plus a design explanation.
Tables abbreviate the schema: return full id/purpose/instructions/rationale/isolated_context/
cue fields and framework_mapping, with no context-policy names or dependency references.

A. BUSINESS STRATEGY
Brief: 'Suggest a growth strategy for an independent bicycle repair shop.'
Selected framework: Access-led growth through Jobs to Be Done (adapted from Christensen and
collaborators). Required components: Access barrier, Repeatable access model, Delivery trade-off,
Demand test. Preserve desired progress in specific circumstances; a proposed pilot is not research.

id | decision owned; boundaries; meaningful variation
market_horizon | Proposed local context and pilot horizon, with unknowns labeled assumptions;
  no invented demand figures or growth tactic.
audience_friction | Customer circumstances, functional/social/emotional progress and switching
  barrier; no delivery decision. Vary the job and forces preventing progress.
outside_pattern | isolated_context=true; cue 'ways shared resources become available at
  predictable times'; describe a neutral operating rule, with no shop/customer context.
access_model | Repeatable access model preserving the selected job/barrier; vary coordination,
  location and responsibility; no pricing, staffing increases or pilot results.
delivery_tradeoff | Capacity commitment and explicit sacrifice supporting the access model;
  do not replace the selected service or invent staff.
pattern_integration | Make the outside rule improve the access mechanism; no decorative analogy.
pilot_and_measure | Test the selected job and access hypothesis with proposed observations,
  bookings and failure criteria; do not claim the experiment has happened.
strategy_outline | Coherent delivery and pilot outline preserving all selected decisions.

framework_mapping: Access barrier → audience_friction; Repeatable access model → access_model,
pattern_integration; Delivery trade-off → delivery_tradeoff; Demand test → pilot_and_measure.
Even the isolated node waits its turn; isolation controls what it sees, not scheduling.

B. ADVERTISING
Brief: 'Create a short ad concept for a reusable lunch container. Only supplied product facts:
removable compartments and a transparent lid.'
Selected original framework: Demonstration and response.
Required components: Audience tension, Observable product truth, Demonstration, Next action.

channel_moment | Placement, duration and attention conditions; no chosen hook or invented reach.
audience_tension | A relevant lunch-packing frustration, not a complete ad idea.
voice_rules | Tone plus operational language/performance rules; no new product claims.
outside_pattern | isolated_context=true; cue 'everyday ways hidden arrangements are revealed';
  describe a neutral process, with no container/advertising context.
proof_mechanism | Demonstrate an actual supplied feature in the selected medium. With an audio
  placement, audible/spoken demonstration must work without on-screen text; no leak-proof claims.
creative_device | Integrate the neutral reveal rule into the demonstration. Vary interaction,
  information order or reveal logic; do not just rename the same scene.
hook_execution | Opening and executable sequence preserving channel, voice, device and proof.
response_payoff | Product-connected payoff and next action consistent with the execution.

framework_mapping: Audience tension → audience_tension; Observable product truth → proof_mechanism;
Demonstration → proof_mechanism, creative_device, hook_execution; Next action → response_payoff.
Applicability counterexample: for generic water without special product facts, do NOT demand
laboratory proof or an existing brand asset. Adapt to an honestly described occasion or creative
association. Do not call a quiet scene evidence of purity, health or special performance.

C. STORY PLOT
Brief: 'Outline a story about a lighthouse keeper.'
Selected original framework: Transformation through a consequential choice.
Required components: Inner contradiction, Pressure, Turning choice, Changed ending.

inner_contradiction | Desire opposed by protective belief; leave events and ending open.
setting_time | Location, season/era and material environmental rule affecting available actions.
voice_rules | Perspective plus concrete prose rules changing how information reaches the reader.
outside_pattern | isolated_context=true; cue 'ways people maintain a connection across an
  interruption'; describe a neutral process and rule, with no keeper/lighthouse references.
central_pressure | Conflict making the selected belief costly; no response or convenient rescue.
turning_choice | Opening behavior, decisive choice and changed ending as one coherent bundle.
cast_structure | Complete cast functions and structure supporting the selected change.
pattern_payoff | Give the neutral process a consequential role in an action or payoff.
causal_outline | Outline earning the locked outcome in the chosen setting, structure and voice.

framework_mapping: Inner contradiction → inner_contradiction; Pressure → central_pressure;
Turning choice → turning_choice, causal_outline; Changed ending → turning_choice, pattern_payoff,
causal_outline. Mystery would require a different ordered list with hidden truth and clues.

SOURCE-TO-WORKFLOW CONTRASTS
Porter positioning: value_proposition → activity_configuration → deliberate_exclusions →
activity_fit → strategy_outline. Fit explores coherent implementations, not rerolling choices.
Campaign strategy adapted from Les Binet and Peter Field's The Long and the Short of It (IPA;
research using effectiveness cases, including agency practice associated with adam&eveDDB):
time_horizon → brand_and_activation_roles → distinct_creative_jobs → coordinated_execution →
short_and_long_term_measurement. Do not turn context-dependent findings into a universal budget
ratio. This is a campaign method, not a mandatory method for one short product ad.
The original ad/story approaches above demonstrate mechanics; prefer suitable established
methods or explicit adaptations in actual Node 0 pools.

SCOPE-LEAK COUNTEREXAMPLE
A format node asked only for duration, aspect ratio and sound must NOT answer '12 seconds,
open with What is this called?, reveal the bottle, close on the name'. That spends choices
owned by later nodes. A valid format candidate is '12 seconds, vertical 9:16, sound-off-first,
readable text, at most three attention beats; hook and visual sequence remain open'.
A question node must return its question/creative tension, not a repeated three-shot script.
Sparse product facts do not require recognition-only questions: hypothetical participation,
observational humor and everyday dilemmas can be creative proposals without invented claims.

EXAMPLE OF ONE FULL NODE (from workflow A)
{
  "id": "access_model",
  "purpose": "Choose how the selected customer reaches the service.",
  "instructions": "Generate k distinct access models preserving all earlier selected context, the customer and barrier. Each candidate owns only location, coordination and responsibility. Do not choose pricing, staffing increases or pilot results. Vary the delivery mechanism, not its wording.",
  "rationale": "Access must remove the selected friction before capacity commitments are chosen.",
  "isolated_context": false,
  "cue": null
}
Replace demonstration k in actual node instructions with the requested candidate count.
"""

CANDIDATE_POOLS = """WORKED GENERATION EXAMPLES — each independent demonstration has k=5
These show what a varied pool for ONE node looks like. They are not alternatives you should
copy into another request. Only the current node's available context may influence its output.

A. BUSINESS: access_model
Locked context: one shop; no added mechanics; weekday commuters find ordinary shop visits
inconvenient. Node owns access/coordination, not prices, staffing or a full growth plan.
{
  "candidates": [
    "Collection lockers at existing premises: customers leave bikes before opening and approve work remotely; mechanics still repair in the shop.",
    "One neighborhood collection circuit: a scheduled courier brings several commuter bikes to the shop together and returns them on a fixed route.",
    "Customer-organized group handover: one volunteer at an apartment building coordinates a shared pickup with the shop; the shop gains a single contact point.",
    "Employer-hosted repair days: the existing mechanic visits one workplace at a time for prebooked work, moving access to where commuters already spend the day.",
    "Remote triage before handover: customers show the bike in a booked video slot; the shop identifies which jobs need a physical appointment before the customer travels."
  ]
}
Different mechanisms: asynchronous handover, logistics aggregation, customer coordination,
moving the service, and separating diagnosis from handover. These are proposals; availability is not
asserted. 'Fast repairs', 'quicker repairs', 'speedy repairs' would not constitute this variety.

B. ADVERTISING: proof_mechanism
Locked context: removable lunch-container compartments, transparent lid, short visual ad;
audience dislikes a monotonous lunch routine. Own the demonstration, not copy or unproven claims.
{
  "candidates": [
    "Reconfiguration: a top-down shot rearranges the removable compartments into three different lunch layouts; each arrangement stays visible through the lid.",
    "Viewer prediction: the closed transparent lid reveals the current layout; a hand removes one compartment and the viewer anticipates how the space will change.",
    "Parallel choices: two people arrange the same components differently, showing that the container supports different preferences without claiming one is healthier.",
    "Reverse assembly: begin with an arranged lunch under the clear lid, then remove each compartment to expose how that arrangement was constructed.",
    "Partial reveal: opaque paper temporarily masks parts of the transparent lid; uncovering sections reveals the actual arrangement underneath, then the whole lid is shown."
  ]
}
Different mechanisms: transformation, participation, comparison, decomposition and reveal.
The node does not quietly add leak resistance, refrigeration or fabricated testimonials.

C. STORY: voice_rules
Locked context: lighthouse keeper, isolation, responsibility. Own only voice/perspective.
{
  "candidates": [
    "A first-person maintenance log: short practical entries; emotional changes become visible through what the keeper stops recording.",
    "Close third-person sensory prose: describe wind, vibration and light before naming feelings; reveal only what the keeper can perceive.",
    "Retrospective oral narration: a former apprentice addresses a skeptical listener; repeated phrases gain a different meaning as the account develops.",
    "An exchange of unsent letters: second-person address exposes the gap between what the keeper reports and what they cannot ask for directly.",
    "Detached procedural narration: impersonal rules about maintaining a light gradually expose the human cost of following them literally."
  ]
}
The alternatives change narration and information access, not just labels like 'evocative'.
None selects the incident, supporting cast or ending on behalf of later nodes.

D. STORY: setting_time
Locked context: lighthouse keeper; location/time remain open. Own conditions, not events.
{
  "candidates": [
    "A tidal island in late autumn, before radio communication; the causeway is usable only at low tide.",
    "An equatorial volcanic coast during monsoon season, in the present; heavy rain obscures visual signals while the harbor remains busy.",
    "A high-latitude harbor during the first weeks of polar night, after partial automation; darkness lengthens duty while maintenance access becomes seasonal.",
    "A floating beacon on a nineteenth-century river delta during flood season; the channel shifts, so a useful signal depends on local knowledge.",
    "A former lighthouse beside a modern city in midsummer; it is now a public landmark, and the keeper's work happens under constant observation."
  ]
}
Different combinations alter access, visibility, infrastructure and social exposure. No entry
already contains a storm rescue, argument, turning choice or conclusion.

E. ISOLATED INSPIRATION: outside_pattern
Only available context: instructions 'Describe a neutral process and its operating rule';
cue 'everyday ways hidden arrangements are revealed'. No business, ad or story brief is seen.
{
  "candidates": [
    "Unfolding a paper map: a sequence of folds becomes visible as one connected arrangement.",
    "Lifting a stencil: empty spaces reveal the shape of the pattern that organized them.",
    "Cutting a layered loaf: one cross-section exposes an arrangement hidden by the exterior.",
    "Switching a room's lights off in sequence: remaining illumination reveals which areas share a source.",
    "Sorting a mixed drawer by use rather than appearance: functional relationships replace superficial similarity."
  ]
}
These supply different usable rules. A later integration node, with the real brief and
selected values, must turn the chosen rule into a mechanism, action or payoff. This isolated
generator must not guess which domain will eventually use its output.

F. ADVERTISING: viewer_question
Locked context: a generic water bottle; short visual Reel; no known performance or origin
claims. The framework permits an open creative question, not specifically name recognition.
Own only the question and the kind of engagement it invites; do not choose shots or answers.
{
  "candidates": [
    "What deserves a pause today? — invites a personal choice rather than product trivia.",
    "If your to-do list could talk, would it ever let you stop? — introduces a comic hypothetical conflict.",
    "Can you spot the one thing in this moment that isn't rushing? — opens an observational puzzle.",
    "Who wins: the voice saying one more errand, or the voice saying take a minute? — sets up an inner debate.",
    "How would you spend twelve seconds that nobody asked you to be productive? — offers a small audience challenge."
  ]
}
These open different engagement mechanisms, not five ways to ask 'What is the name?'. None
asserts that the water changes health, mood or performance. If an actual earlier selection
requires name recognition, these options would be invalid; the framework/planner must avoid
creating that unnecessary restriction in the first place.

Selections in this explanation would be made by Python after generation. Do not add a
'selected', 'best', ranking, or explanation field to the actual candidate-pool response.
"""

COMPOSITIONS = """WORKED COMPOSITION EXAMPLES — selected inputs, not new choices
Show the actual work first, then explain the framework and every selected dimension. These
compact demonstrations illustrate both sections; substantial briefs need fuller development.
Do not replace the artifact with an explanation or replace the explanation with a generic line.

A. BUSINESS
Brief: propose one small growth pilot for a bicycle repair shop.
Locked dimensions: local employer pilot; commuting customers unable to visit during work;
employer-hosted repair days; one existing mechanic; protect existing shop appointments;
neutral inspiration 'predictable access windows'; validate bookings rather than stated interest.
Framework: access-focused adaptation of Jobs to Be Done, not a completed customer study.

FINISHED PILOT
Offer one prebooked repair window at a nearby employer. Employees book before the visit and
state the repair needed; the existing mechanic accepts only jobs fitting an available slot.
Bring the accepted work to the employer window, deferring complex jobs to a separately agreed
shop appointment. Cap participation at actual spare capacity so current shop bookings remain
protected. Offer the next window only after reviewing confirmed bookings, completed jobs and
whether existing appointments were disrupted. Employer participation and paid demand remain
testable assumptions; no revenue or customer count has been established.

WHY THESE DIMENSIONS MATTER
- Framework: the offer responds to progress blocked by circumstances, rather than assuming
  commuters want a discount. Its access emphasis and pilot are explicit adaptations.
- Market/horizon: one employer and one window bound the commitment and make learning practical.
- Customer/job: workday access is the obstacle; workplace service changes access directly.
- Access mechanism: the mechanic travels to prebooked demand instead of extending shop hours.
- Capacity/trade-off: one mechanic and protected bookings exclude unlimited walk-up repairs.
- Inspiration/integration: predictable windows turn scattered requests into a coordinated slot.
- Measurement/outline: bookings and disruption determine the next commitment, not compliments.
The design trades flexibility for predictable capacity. Validate willingness to book and the
employer's cooperation before treating this as a scalable strategy.

B. AUDIO AD
Brief: a short water ad; no special features or brand assets are supplied.
Locked dimensions: traveler between errands at a bus stop; 10–15-second audio; bright,
conversational voice with one short question; rhythmic errand-list interrupted by a sip;
occasion-based water break, not evidence of a product effect; next action 'take a sip'.
Framework: original occasion-led micro-scene, with no claim of external validation.

FINISHED AUDIO SCRIPT — approximately 12–15 seconds, verify with a read-through
[SFX: quick footsteps stop. A distant bus idles.]
VOICE, brisk and bright: 'Keys. Bags. Next bus. Got a moment?'
[SFX: one audible sip; a short beat.]
VOICE, relaxed but still conversational: 'A bottle of water. A sip between stops.
While you're waiting, take a sip.'

HOW THE SELECTIONS SHAPE IT
- Framework/benefit: the bottle belongs to an ordinary occasion; the pause is a creative
  association, not proof of a calming or health effect.
- Audience/setting: errands, waiting and transit sound establish the selected traveler.
- Medium/duration: all information is audible; no caption or unseen shot carries the idea.
- Voice: compact phrasing, a direct address and one question give the selected brightness.
- Device/execution: the rhythmic list is interrupted by the actual sip, changing pace through
  sound rather than describing a visual scene the listener cannot see.
- Response: 'take a sip' connects the closing action to water instead of generic relaxation.
The short beat is an execution choice, not a therapeutic claim. No special product property,
availability, endorsement or existing brand identity is implied.

C. STORY PLOT
Brief: outline a lighthouse-keeper story, not a complete prose story.
Locked dimensions: maintenance-log voice; tidal causeway; belief that asking for help is
failure; outside pattern 'a relay keeps a connection alive'; growing maintenance backlog;
apprentice as second cast member; ending in which the keeper requests a second pair of hands.
Framework: original transformation-through-choice approach; no borrowed authority claimed.

FINISHED PLOT
The keeper's log records each task as completed alone. The causeway opens only at low tide,
and a visiting apprentice notices repairs still waiting beneath confident entries. The keeper
sends the apprentice away rather than admit the backlog. With the next access window nearing,
the keeper tries to finish every task and discovers that the unreported work now threatens
the light's next operation. Completing the log honestly means admitting the system cannot be
maintained alone. The keeper records unfinished tasks and requests the apprentice's help
before the next tide closes the route. They divide the maintenance into a relay: one keeps
the light operating while the other finishes a repair. The final log lists two workers.

HOW THE CHOICES WORK TOGETHER
- Framework/contradiction: the belief equating help with failure creates the harmful decision;
  requesting help is the visible change, rather than a last-minute solitary rescue.
- Setting/time: tidal access makes delay consequential and bounds when help can arrive.
- Voice: the gap between terse records and actual repairs reveals the keeper's denial.
- Pressure: the backlog arises from earlier choices; no unrelated disaster substitutes for it.
- Cast/structure: the apprentice can notice, be rejected and later participate in the change.
- Inspiration/payoff: the relay becomes a practical maintenance arrangement, not decoration.
- Outcome/outline: the shared final entry demonstrates the locked ending through action.
This is a plot treatment. A request for the full story would require developing its scenes
in the chosen log voice, with this explanatory material kept separate.
"""
