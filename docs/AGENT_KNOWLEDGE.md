# SAARTHI Agent Knowledge Sources

SAARTHI uses a small, versioned public-practice knowledge layer in backend/agent_knowledge.py.

This is not a copy of proprietary model training data. It distills engineering patterns from public documentation and open-source examples into concise execution rules that can be tested and versioned with the application.

## Primary references

- OpenAI platform documentation: https://platform.openai.com/docs/
- Google Gemini code execution: https://ai.google.dev/gemini-api/docs/code-execution
- Google Gen AI Python SDK: https://github.com/googleapis/python-genai
- Anthropic Claude platform documentation: https://docs.anthropic.com/
- xAI API documentation: https://docs.x.ai/
- Meta Llama Cookbook: https://github.com/meta-llama/llama-cookbook

## How this is used

The knowledge layer is injected into the specialist runtime as execution guidance:

1. capability principles
2. workflow sequence
3. quality gates
4. specialist-specific methods where applicable

The model is not treated as the source of truth for deterministic calculations, supplied datasets, source citations, repository state, or completed tool execution.

## Update policy

When a major platform changes its public capabilities, update the distilled rules and add or update regression tests. Do not copy proprietary prompts, hidden system instructions, private datasets, model weights, or copyrighted training corpora into SAARTHI.