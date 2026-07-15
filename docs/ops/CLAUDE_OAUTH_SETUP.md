# Claude OAuth Setup for Pi

**Status: Already configured** — OAuth token exists in `~/.pi/agent/auth.json`.

---

## What you already have

```json
// ~/.pi/agent/auth.json
{
  "anthropic": {
    "type": "oauth",
    "access": "sk-ant-oat01-..."
  }
}
```

This token was obtained from the Anthropic Chrome extension and Pi uses it automatically. No additional setup needed for basic Claude access.

---

## How it works

Pi natively supports Anthropic as a built-in provider. The OAuth flow:

1. **Chrome Extension** stores an OAuth token (visible at `chrome://extensions` → Anthropic → inspect → storage)
2. **Pi reads** `~/.pi/agent/auth.json` where the token is stored as `anthropic.access`
3. **Pi sends** requests to `https://api.anthropic.com/v1/messages` authenticated with the OAuth token
4. The token starts with `sk-ant-oat` — Pi detects this and uses `authToken` instead of `x-api-key`

This is the same pattern used in `gotpapi/launch.ts`:
```typescript
const isOAuth = k.startsWith('sk-ant-oat');
const client = isOAuth
  ? new Anthropic({ authToken: k })
  : new Anthropic({ apiKey: k });
```

---

## Enabling Claude models

### Option A — Use built-in Anthropic models (simplest)

Pi ships with Anthropic models built-in. Just use:

```bash
pi --provider anthropic --model claude-sonnet-4-5
pi --provider anthropic --model claude-haiku-3-5
pi --provider anthropic --model claude-opus-4-7
```

### Option B — Add Claude models with Vision to models.json

For frame visualization, you need a model that accepts images. Add this to `~/.pi/agent/models.json`:

```json
{
  "providers": {
    "claude-vision": {
      "name": "Claude Vision (OAuth)",
      "baseUrl": "https://api.anthropic.com/v1/messages",
      "api": "anthropic-messages",
      "apiKey": "!cat ~/.pi/agent/auth.json | python3 -c \"import json,sys; print(json.load(sys.stdin).get('anthropic',{}).get('access',''))\"",
      "models": [
        {
          "id": "claude-sonnet-4-5",
          "name": "Claude Sonnet 4.5 (Vision)",
          "reasoning": true,
          "input": ["text", "image"],
          "contextWindow": 200000,
          "maxTokens": 8192
        },
        {
          "id": "claude-haiku-3-5",
          "name": "Claude Haiku 3.5 (Vision)",
          "reasoning": false,
          "input": ["text", "image"],
          "contextWindow": 200000,
          "maxTokens": 8192,
          "cost": { "input": 0.80, "output": 4.00, "cacheRead": 0.08, "cacheWrite": 0 }
        }
      ]
    }
  }
}
```

The `apiKey` uses shell command resolution (`!`) to extract the OAuth token from auth.json at runtime.

---

## Using Claude for frame visualization

Once configured, frames extracted by the Flixz service can be described using Claude Vision:

```bash
# Extract frames
curl -X POST http://127.0.0.1:8420/api/flixz/extract \
  -H "Content-Type: application/json" \
  -d '{"video_path": "/path/to/video.mp4", "max_frames": 5}'

# Describe a frame using Claude Vision via Pi
echo "Describe this frame in detail" | pi \
  --provider claude-vision \
  --model claude-sonnet-4-5 \
  --image ~/.pi/flixz/output/<run_id>/frame_0001.png
```

---

## Verifying OAuth works

```bash
# Check auth.json has the token
cat ~/.pi/agent/auth.json | python3 -c "
import json, sys
d = json.load(sys.stdin)
a = d.get('anthropic', {})
print(f'type: {a.get(\"type\")}')
print(f'token: {a.get(\"access\", \"\")[:30]}...')
print(f'is_oauth: {a.get(\"access\", \"\").startswith(\"sk-ant-oat\")}')
"

# Test Claude is accessible
pi --provider anthropic --model claude-haiku-3-5 --print "Say 'Claude OAuth is working' in exactly 4 words."
```

---

## Token refresh

OAuth tokens from the Chrome extension expire periodically. When they do:

1. Open the Anthropic Chrome extension
2. Log in/sign in to your Claude account
3. The extension refreshes the token automatically
4. Update `~/.pi/agent/auth.json` with the new token value

The gotpapi project reads the token from auth.json at launch time. Pi does the same on every request.

---

## Default model in settings

To make Claude the default, update `~/.pi/agent/settings.json`:

```json
{
  "defaultProvider": "anthropic",
  "defaultModel": "claude-sonnet-4-5"
}
```

Or keep the current `agua` provider for general use and use `claude-vision` only for frame visualization tasks.
