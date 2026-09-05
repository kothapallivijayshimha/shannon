// Copyright (C) 2025 Keygraph, Inc.
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License version 3
// as published by the Free Software Foundation.

/**
 * Model tier definitions and resolution.
 *
 * Three tiers mapped to capability levels:
 * - "small"  (Haiku — summarization, structured extraction)
 * - "medium" (Sonnet — tool use, general analysis)
 * - "large"  (Opus — deep reasoning, complex analysis)
 *
 * Users override via ANTHROPIC_SMALL_MODEL / ANTHROPIC_MEDIUM_MODEL / ANTHROPIC_LARGE_MODEL,
 * which works across all providers (direct, Bedrock, Vertex).
 */

export type ModelTier = 'small' | 'medium' | 'large';

const DEFAULT_MODELS: Readonly<Record<ModelTier, string>> = {
  small: 'claude-haiku-4-5-20251001',
  medium: 'claude-sonnet-4-6',
  large: 'claude-opus-4-7',
};

const DEFAULT_OLLAMA_MODELS: Readonly<Record<ModelTier, string>> = {
  small: 'llama3.2:3b',
  medium: 'qwen2.5:14b',
  large: 'qwen2.5:32b',
};

/** Resolve a model tier to a concrete model ID. */
export function resolveModel(tier: ModelTier = 'medium', provider?: string): string {
  if (provider === 'ollama' || process.env.SHANNON_LLM_PROVIDER === 'ollama') {
    const configured = process.env[`OLLAMA_${tier.toUpperCase()}_MODEL`];
    return configured || process.env.OLLAMA_MODEL || DEFAULT_OLLAMA_MODELS[tier];
  }

  switch (tier) {
    case 'small':
      return process.env.ANTHROPIC_SMALL_MODEL || DEFAULT_MODELS.small;
    case 'large':
      return process.env.ANTHROPIC_LARGE_MODEL || DEFAULT_MODELS.large;
    default:
      return process.env.ANTHROPIC_MEDIUM_MODEL || DEFAULT_MODELS.medium;
  }
}

/** Whether a model supports adaptive thinking. Opus 4.6 and 4.7 only. */
export function supportsAdaptiveThinking(model: string): boolean {
  return /opus-4-[67]/.test(model);
}
