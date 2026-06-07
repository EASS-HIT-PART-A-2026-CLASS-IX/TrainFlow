# TrainFlow Coach Service

AI-powered, history-aware workout planner. Reads the exercise catalog and recent
workout history from the exercise-service over HTTP, then produces a
schema-validated workout plan using either an LLM planner (when an Anthropic API
key is configured) or a deterministic fallback planner.

The LLM may select and order catalog exercises and explain its choices, but every
returned exercise is validated against the live catalog — the model can never
invent an exercise.
