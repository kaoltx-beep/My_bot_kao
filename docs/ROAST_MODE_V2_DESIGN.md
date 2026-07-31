# Roast Mode V2 Design

## Routing priority

Explicit commands and deterministic system routes run before AI. Tool, job, expense, reminder, and memory behavior must not be changed by Roast mode.

## Response flow

1. Route the request.
2. If deterministic/system route matches, execute it and return the result.
3. Otherwise ask the base AI for the factual answer.
4. In Roast mode, pass only the latest user request and the factual base answer to a separate style layer.
5. Validate the styled result. On failure, return the factual base answer.

## Personality state

`personality.py` owns only persistent mode state and prompts. It does not monkey-patch runtime functions.

## Roast constraints

Roast can change tone, humor, teasing, and informal wording. It must not change facts, intent, tool selection, job selection, expense operation, reminder operation, or memory operation.
