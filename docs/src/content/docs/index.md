---
title: Welcome
---

## HICA: Highly Customizable Agent Library

Build AI agents you can trust, trace, and control—every step, every decision.

[![PyPI](https://img.shields.io/pypi/v/hica)](https://pypi.org/project/hica/) [![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/sandipan1/hica/blob/main/LICENSE)

### What is HICA?

HICA is a framework for building customizable, deterministic AI agents. Unlike most frameworks, HICA gives you full control and visibility over every step of your agent's reasoning, tool use, and state. It's designed for developers who want to:

- Debug and audit every decision an agent makes
- Use any tool—MCP tools or local functions
- Include human-in-loop clarifications for trustworthy workflows
- Customize prompts, context, and workflows for maximum control
- Persist and resume conversations with full event history
- Build for reliability, not just demos

![Agent Loop](/excalidraw-animate.svg)

![Agent Workflow](/agent-workflow.png)

### Core principles

- Total Control: own every prompt, tool call, and context window
- Structured Tool Output: separate `llm_content` (for LLM) and `display_content` (for humans)
- Transparent State: event-sourced `Thread` capturing user input, LLM calls, tool calls, responses, and clarifications
- Observability: structured logging and stateful conversations
- Composable Tools: local Python and remote MCP tools in a unified registry
- Human-in-the-Loop: agents can request clarifications or approvals at any step
- Stateful by Design: externalized state for reliability and scale
- Real-Time Event Streaming: yield events for UI updates and audit

Get started with Getting Started and Quickstart, or dive into Architecture and Tools.

