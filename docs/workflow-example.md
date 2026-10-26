# A bear story: framework first, consequential details next

Request: **“Write the plot of a story about a bear.”** This is an illustrative path, not a
hard-coded plan. The application works with other creative requests and frameworks too.
This walkthrough uses the default `CANDIDATE_COUNT=20`. A request's `candidate_count` override
replaces 20 throughout framework generation, planning prompts, node pools and random selection.

## Node 0: different organizing approaches

Generate 20 frameworks before creating the workflow. Each candidate describes its origin,
organizing principle, required components, progression rules and completion criteria.
For example, five of the twenty might be:

| Approach | Organizing principle | Effect on workflow |
| --- | --- | --- |
| Five-second transformation | A brief realization separates contrasting states | Contrast and turning moment precede scenes |
| Mystery and revelation | A central unanswered question drives discovery | Hidden truth, clues, misdirection, revelation |
| Desire, obstacle, consequential choice | Choices under pressure produce change | Desire, resistance, escalation, costly choices |
| Cumulative folktale | Repetition builds a pattern with a meaningful final variation | Repeating situation, variations, pattern-breaking ending |
| Braided perspectives | Viewpoints change the meaning of shared events | Perspectives, incomplete knowledge, convergence |

Python selects one of the twenty uniformly. Assume it selects **five-second transformation**,
honestly labeled as an adapted approach rather than inventing an authoritative attribution.

Its required components are:

1. An emotional contradiction.
2. Contrasting opening and ending behavior.
3. A specific five-second realization that changes a belief or choice.
4. Events that earn the realization and demonstrate its consequences.

The planner sees only this selected framework and the user's request. Other frameworks
cannot influence later generation because their candidates are not passed onward.

## A resulting workflow

Every numbered component below generates **20 complete alternatives**. Python selects one
before the next node generates candidates. Every normal node sees all earlier selections.

| Node ID | Decision and candidate instructions | Context policy |
| --- | --- | --- |
| `emotion` | Twenty tensions, such as wanting closeness while fearing dependence | `isolated_context: false` — all earlier selections |
| `world` | Twenty location/season bundles whose conditions affect events | `isolated_context: false` — all earlier selections |
| `inspiration` | Twenty concrete patterns or phenomena from “ordinary physical processes” | `isolated_context: true` — instructions/cue only |
| `engine` | Twenty premises with desire, obstacle and stakes | `isolated_context: false` — all earlier selections |
| `style` | Twenty voice/perspective combinations affecting how the premise is experienced | `isolated_context: false` — all earlier selections |
| `transformation` | Twenty bundles of opening behavior, a specific five-second realization, and contrasting ending behavior | `isolated_context: false` — all earlier selections |
| `cast_size` | Twenty cast configurations specifying count and dramatic functions | `isolated_context: false` — all earlier selections |
| `cast` | Twenty complete casts of the selected size, with names, desires, relationships and conflicting interpretations | `isolated_context: false` — all earlier selections |
| `acts` | Twenty act configurations earning the selected transformation | `isolated_context: false` — all earlier selections |
| `detail` | Twenty ways to make the selected isolated inspiration affect conflict or payoff | `isolated_context: false` — all earlier selections |
| `outline` | Twenty causal outlines following the selected acts and earning the turning moment | `isolated_context: false` — all earlier selections |

All nodes run sequentially in the table's order, including `inspiration`. The context flag
only controls inputs. `inspiration` receives no story information; `engine` and every later
normal node receive its selected pattern along with all earlier choices. The application
never passes unselected pools onward. No dependency lists or branching are needed.

The framework mapping makes the design reviewable:

| Framework obligation | Nodes fulfilling it |
| --- | --- |
| Emotional contradiction | emotion, engine |
| Contrasting opening and ending behavior | transformation, outline |
| Five-second realization | transformation, outline |
| Events earning the realization and demonstrating consequences | engine, acts, outline |

Framework obligations and mapped node IDs are validated structurally. Whether the generated
content actually fulfills those obligations remains a semantic quality question.

## One illustrative selected path

- **Contradiction:** the bear wants companionship but believes accepting help creates an
  unbearable debt.
- **World:** a mountain village during an unusually early thaw.
- **Isolated inspiration:** the temporary wooden form supporting an arch during construction.
- **Story engine:** the bear secretly repairs a communal bridge so nobody can claim he needs
  the village.
- **Transformation:** trapped beneath the failing bridge, he sees villagers abandon their
  possessions to hold his escape route open. In five seconds, he recognizes that their help
  is a choice to stand beside him rather than a claim against him.
- **Ending contrast:** he asks for help rebuilding, then leaves a place beside him for
  someone else.
- **Consequential detail:** temporary bridge supports recur as practical objects and as an
  image of help that enables strength without becoming a permanent obligation.

The temporary support is not simply decoration. It connects construction, rescue, the bear's
belief and the ending action. That is the intended kind of nonstandard combination: a
separately generated input becomes meaningful through later decisions.

## Final composition and review

The writer receives the original request, selected framework, ordered workflow and all selected
values. It develops the complete plot without selecting again, discarding an awkward choice,
changing cast size, or replacing a name. The output also explains each selected dimension:
why the thaw changes the bridge conflict, how perspective shapes information, how the chosen
cast earns the realization, and where the temporary support affects both action and payoff.
The finished plot and supporting design explanation are distinct parts of one document.
The response retains the selections and optional pools.

Review four things: does the framework change the structure; do broad decisions lead the
details; do details change what happens; and does the finished output preserve the selected
path? Do not expect randomness alone to guarantee quality or originality.
