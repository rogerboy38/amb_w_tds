# Raven AI Agent - Session Handout

## Project Overview
- **Repo:** https://github.com/rogerboy38/raven_ai_agent
- **Framework:** Frappe/ERPNext
- **Purpose:** Multi-provider AI agent for ERPNext

## Current Status

### ✅ Working Providers
1. **OpenAI** - Fully functional
2. **DeepSeek** - Fully functional

### 🔧 In Progress: MiniMax
**Latest Error:** `invalid chat setting`

**Last Fix (commit e4fcbab):**
- Changed model to `MiniMax-M1`
- Added `name` field to messages
- Changed `max_tokens` → `max_completion_tokens`

**Key File:** `raven_ai_agent/providers/minimax.py`

**API Details:**
- Endpoint: `https://api.minimax.io/v1/text/chatcompletion_v2`
- Requires: `name` field in each message
- Models: `MiniMax-M1`, `MiniMax-M2.1`

## Test Commands
```bash
git pull origin main
bench console
```

```python
from raven_ai_agent.api.agent_v2 import RaymondLucyAgentV2

# Test OpenAI
agent = RaymondLucyAgentV2(user="Administrator")
print(agent.process_query("Hello"))

# Test DeepSeek
agent = RaymondLucyAgentV2(user="Administrator", provider_override="deepseek")
print(agent.process_query("Hello"))

# Test MiniMax
agent = RaymondLucyAgentV2(user="Administrator", provider_override="minimax")
print(agent.process_query("Hello"))
```

## Key Files
- `api/agent_v2.py` - Main agent class `RaymondLucyAgentV2`
- `providers/minimax.py` - MiniMax provider (needs fixes)
- `providers/deepseek.py` - DeepSeek provider (working)
- `providers/openai_provider.py` - OpenAI provider (working)

## Resolved Issues This Session
1. Migration `MandatoryError` on `default_provider` - removed `reqd: 1`
2. OpenAI key retrieval - fixed `hasattr` check
3. `CostMonitor` init args - removed settings param
4. `return_usage` param - removed from chat call
5. DeepSeek null model - added `self.model = self.default_model`
6. MiniMax URL - changed to `api.minimax.io`
7. MiniMax model names - updated to `MiniMax-M1`

## Next Steps
1. Debug remaining MiniMax "invalid chat setting" error
2. May need to check MiniMax API key format or additional required params
3. Consider testing with curl directly to isolate issue
