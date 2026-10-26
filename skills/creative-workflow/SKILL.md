---
name: creative-workflow
description: Develop creative ads, stories, strategies, or concepts through framework-led decisions and code-selected alternatives in a single conversation. Use when the user wants deliberately varied creative outcomes with inspectable random choices.
---

# Creative workflow

Run the whole creative process yourself in one context window, using the harness's code
execution tool for random selection. This is a prompt-driven method, not a request to start
the external Creative service, call another LLM, or build software.

## Operating rules

- Use `k=20` alternatives for frameworks and each decision unless the user specifies another
  positive count. Keep pools concise enough to fit the context. Choose a manageable number of
  consequential steps; at most 23 after the framework. Do not silently lower k or truncate pools.
- Generate each complete pool before selecting. Put that exact pool into the code tool and
  use OS-backed randomness, such as Python `secrets.randbelow(k)`, to select uniformly.
  Never invent a random number, choose a favorite, rank, reroll, or redraw an awkward result.
- Lock each selected value. Later steps develop its consequences rather than replace it.
  Preserve explicit user constraints and distinguish supplied facts from creative proposals.

A minimal selector to execute in the code tool:

```python
import secrets


def choose(pool, k):
    if len(pool) != k or k < 1:
        raise ValueError("Commit exactly k candidates before selecting")
    index = secrets.randbelow(k)
    return {"selected_index": index, "selected_value": pool[index]}
```

Pass the complete actual pool as `pool` and the agreed count as `k`; execute and print the
returned object. Use only the index and value actually returned by the tool. Retain the
pool and selection in the session so they remain inspectable. No installed project code is
required. If code execution is unavailable, explain that real code-backed selection cannot
be performed and request a code-capable harness; do not simulate random selection in prose.

## Process

1. **Framework first.** Generate k materially different approaches suitable for the brief.
   For each, give a name, honest origin (established/adapted/original), author or work when
   confidently known, organizing principle, required components, progression rules, and
   completion criteria. Prefer relevant established methods; identify what an adaptation
   changes. Do not invent citations or imply that practitioner guidance is scientific proof.
   Every option must work with the available information: missing product evidence does not
   justify invented claims, but also does not limit creativity to stating a product's name.
   Execute the selector once. Plan around the selected framework.

2. **Plan an ordered workflow.** Turn the selected framework into concrete decisions, mapping
   every required component to at least one node. List each node's ID, purpose, instructions,
   concise rationale, and what later decisions it leaves open. Use high-impact differences
   before cascading details: context/format, audience or tension, mechanism, voice, structure,
   consequences and execution as relevant. A format node must not prewrite its hook or ending.
   Freeze the list before generating its pools. Bundles can contain a complete cast or other
   coupled decisions; do not add nodes dynamically after a quantity is selected.

3. **Generate, select, develop.** Process nodes sequentially. Generate k distinct, nonempty
   alternatives for only the current decision, using the brief, framework and all earlier
   locked selections. Put the complete pool in the code tool, execute the selector once,
   record its returned index/value, then move on. Do not generate later pools before the
   earlier selection is known.

   Alternatives must lead to recognizably DIFFERENT final outcomes, with rippling effects
   on future choices. Ask: if A replaced B, what later action, structure, trade-off, experience
   or payoff would have to change? If the same finished work fits both after a few words are
   swapped, the pool is too superficial. Different voices should change information delivery;
   different settings should change available actions; different business mechanisms should
   change roles, economics or tests. Do not put several complete future executions inside a
   narrow node or repeat locked context in every candidate.

   Examples of consequential differences: an ad built around a viewer puzzle versus a
   character debate changes participation, staging and payoff; a tidal island versus a city
   landmark changes access and available help; employer-hosted repairs versus customer-run
   maintenance changes capacity, responsibility and validation. Mere paraphrases do not.

   Optionally include neutral outside inspiration and a later integration step that makes
   its selected rule functional. In one context window, you cannot truly hide prior content
   or unselected pools from yourself. Treat cue-only inspiration and selected-only development
   as working disciplines, not claims of technical isolation. Do not claim the service's
   separate-call context boundaries apply here.

4. **Compose and explain.** Develop one complete artifact in the requested format, preserving
   locked choices and their consequences. Keep medium-specific execution detail: an audio ad
   needs audible delivery; a visual reel needs shots/copy/pacing; a strategy needs operating
   implications; a plot needs causal events and an earned outcome. Follow it with the selected
   framework and a concise table of node, selected value, returned zero-based index, and
   concrete effect on the result. Explain interactions and material assumptions without
   exposing private reasoning. Include full pools if requested. If the user requires only
   the artifact or limits the entire response, respect that presentation constraint while
   retaining the selection record in the session.

Random selection does not guarantee diverse candidates or a faithful final composition.
Make those qualities visible through the actual alternatives, locked choices, and their effects.
