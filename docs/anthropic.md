# Anthropic Claude Docs

## [Working with the Messages API](https://docs.claude.com/en/docs/build-with-claude/working-with-messages)

> Practical patterns and examples for using the Messages API effectively

This guide covers common patterns for working with the Messages API, including basic requests, multi-turn conversations, prefill techniques, and vision capabilities. For complete API specifications, see the [Messages API reference](https://docs.claude.com/en/api/messages).

### Basic request and response

```bash
#!/bin/sh
curl https://api.anthropic.com/v1/messages \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-sonnet-4-5",
    "max_tokens": 1024,
    "messages": [
        {"role": "user", "content": "Hello, Claude"}
    ]
}'
```

```Python
import anthropic

message = anthropic.Anthropic().messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, Claude"}
    ]
)
print(message)
```

```TypeScript
import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic();

const message = await anthropic.messages.create({
  model: 'claude-sonnet-4-5',
  max_tokens: 1024,
  messages: [
    {"role": "user", "content": "Hello, Claude"}
  ]
});
console.log(message);
```

```JSON
{
  "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Hello!"
    }
  ],
  "model": "claude-sonnet-4-5",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 12,
    "output_tokens": 6
  }
}
```

### Multiple conversational turns

The Messages API is stateless, which means that you always send the full conversational history to the API. You can use this pattern to build up a conversation over time. Earlier conversational turns don't necessarily need to actually originate from Claude — you can use synthetic `assistant` messages.

```bash
#!/bin/sh
curl https://api.anthropic.com/v1/messages \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-sonnet-4-5",
    "max_tokens": 1024,
    "messages": [
        {"role": "user", "content": "Hello, Claude"},
        {"role": "assistant", "content": "Hello!"},
        {"role": "user", "content": "Can you describe LLMs to me?"}

    ]

}'

```

```Python
import anthropic

message = anthropic.Anthropic().messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello, Claude"},
        {"role": "assistant", "content": "Hello!"},
        {"role": "user", "content": "Can you describe LLMs to me?"}
    ],
)
print(message)

```

```TypeScript
import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic();

await anthropic.messages.create({
  model: 'claude-sonnet-4-5',
  max_tokens: 1024,
  messages: [
    {"role": "user", "content": "Hello, Claude"},
    {"role": "assistant", "content": "Hello!"},
    {"role": "user", "content": "Can you describe LLMs to me?"}
  ]
});
```

```JSON
{
    "id": "msg_018gCsTGsXkYJVqYPxTgDHBU",
    "type": "message",
    "role": "assistant",
    "content": [
        {
            "type": "text",
            "text": "Sure, I'd be happy to provide..."
        }
    ],
    "stop_reason": "end_turn",
    "stop_sequence": null,
    "usage": {
      "input_tokens": 30,
      "output_tokens": 309
    }
}
```

### Putting words in Claude's mouth

You can pre-fill part of Claude's response in the last position of the input messages list. This can be used to shape Claude's response. The example below uses `"max_tokens": 1` to get a single multiple choice answer from Claude.

```bash
#!/bin/sh
curl https://api.anthropic.com/v1/messages \
     --header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-sonnet-4-5",
    "max_tokens": 1,
    "messages": [
        {"role": "user", "content": "What is latin for Ant? (A) Apoidea, (B) Rhopalocera, (C) Formicidae"},
        {"role": "assistant", "content": "The answer is ("}
    ]
}'
```

```Python
import anthropic

message = anthropic.Anthropic().messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1,
    messages=[
        {"role": "user", "content": "What is latin for Ant? (A) Apoidea, (B) Rhopalocera, (C) Formicidae"},
        {"role": "assistant", "content": "The answer is ("}
    ]
)
print(message)
```

```TypeScript
import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic();

const message = await anthropic.messages.create({
  model: 'claude-sonnet-4-5',
  max_tokens: 1,
  messages: [
    {"role": "user", "content": "What is latin for Ant? (A) Apoidea, (B) Rhopalocera, (C) Formicidae"},
    {"role": "assistant", "content": "The answer is ("}
  ]
});
console.log(message);
```

```JSON
{
  "id": "msg_01Q8Faay6S7QPTvEUUQARt7h",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "C"
    }
  ],
  "model": "claude-sonnet-4-5",
  "stop_reason": "max_tokens",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 42,
    "output_tokens": 1
  }
}
```

For more information on prefill techniques, see our [prefill guide](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/prefill-claudes-response).

### Vision

Claude can read both text and images in requests. We support both `base64` and `url` source types for images, and the `image/jpeg`, `image/png`, `image/gif`, and `image/webp` media types. See our [vision guide](https://docs.claude.com/en/docs/build-with-claude/vision) for more details.

```bash
#!/bin/sh

#### Option 1: Base64-encoded image

IMAGE_URL="https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg" IMAGE_MEDIA_TYPE="image/jpeg" IMAGE_BASE64=$(curl "$IMAGE_URL" | base64)

curl https://api.anthropic.com/v1/messages \
--header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-sonnet-4-5",
    "max_tokens": 1024,
    "messages": [
        {"role": "user", "content": [
            {"type": "image", "source": {
                "type": "base64",
                "media_type": "'$IMAGE_MEDIA_TYPE'", "data": "'$IMAGE_BASE64'" }}, {"type": "text", "text": "What is in the above image?"} ]} ] }'

#### Option 2: URL-referenced image

curl https://api.anthropic.com/v1/messages \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{ "model": "claude-sonnet-4-5", "max_tokens": 1024, "messages": [ {"role": "user", "content": [ {"type": "image", "source": { "type": "url", "url": "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg" }}, {"type": "text", "text": "What is in the above image?"} ]} ] }'

```

```Python
import anthropic
import base64
import httpx

## Option 1: Base64-encoded image
image_url = "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
image_media_type = "image/jpeg"
image_data = base64.standard_b64encode(httpx.get(image_url).content).decode("utf-8")

message = anthropic.Anthropic().messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_media_type,
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": "What is in the above image?"
                }
            ],
        }
    ],
)
print(message)

## Option 2: URL-referenced image
message_from_url = anthropic.Anthropic().messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "url",
                        "url": "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg",
                    },
                },
                {
                    "type": "text",
                    "text": "What is in the above image?"
                }
            ],
        }
    ],
)
print(message_from_url)
```

```TypeScript
import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic();

// Option 1: Base64-encoded image
const image_url = "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
const image_media_type = "image/jpeg"
const image_array_buffer = await ((await fetch(image_url)).arrayBuffer());
const image_data = Buffer.from(image_array_buffer).toString('base64');

const message = await anthropic.messages.create({
  model: 'claude-sonnet-4-5',
  max_tokens: 1024,
  messages: [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_media_type,
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": "What is in the above image?"
                }
            ],
        }
      ]
});
console.log(message);

// Option 2: URL-referenced image
const messageFromUrl = await anthropic.messages.create({
  model: 'claude-sonnet-4-5',
  max_tokens: 1024,
  messages: [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "url",
                        "url": "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg",
                    },
                },
                {
                    "type": "text",
                    "text": "What is in the above image?"
                }
            ],
        }
      ]
});
console.log(messageFromUrl);
```

```JSON
{
  "id": "msg_01EcyWo6m4hyW8KHs2y2pei5",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "This image shows an ant, specifically a close-up view of an ant. The ant is shown in detail, with its distinct head, antennae, and legs clearly visible. The image is focused on capturing the intricate details and features of the ant, likely taken with a macro lens to get an extreme close-up perspective."
    }
  ],
  "model": "claude-sonnet-4-5",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 1551,
    "output_tokens": 71
  }
}
```

### Tool use, JSON mode, and computer use

See our [guide](https://docs.claude.com/en/docs/agents-and-tools/tool-use/overview) for examples for how to use tools with the Messages API. See our [computer use guide](https://docs.claude.com/en/docs/agents-and-tools/tool-use/computer-use-tool) for examples of how to control desktop computer environments with the Messages API.

---

## [Prompt caching](https://docs.claude.com/en/docs/build-with-claude/prompt-caching)

Prompt caching is a powerful feature that optimizes your API usage by allowing resuming from specific prefixes in your prompts. This approach significantly reduces processing time and costs for repetitive tasks or prompts with consistent elements.

Here's an example of how to implement prompt caching with the Messages API using a `cache_control` block:

```bash
curl https://api.anthropic.com/v1/messages \
  -H "content-type: application/json" \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "claude-sonnet-4-5",
    "max_tokens": 1024,
    "system": [
      {
        "type": "text",
        "text": "You are an AI assistant tasked with analyzing literary works. Your goal is to provide insightful commentary on themes, characters, and writing style.\n"
      },
      {
        "type": "text",
        "text": "<the entire contents of Pride and Prejudice>",
        "cache_control": {"type": "ephemeral"}
      }
    ],
    "messages": [
      {
        "role": "user",
        "content": "Analyze the major themes in Pride and Prejudice."
      }
    ]
  }'

### Call the model again with the same inputs up to the cache checkpoint

curl https://api.anthropic.com/v1/messages # rest of input

```

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    system=[
      {
        "type": "text",
        "text": "You are an AI assistant tasked with analyzing literary works. Your goal is to provide insightful commentary on themes, characters, and writing style.\n",
      },
      {
        "type": "text",
        "text": "<the entire contents of 'Pride and Prejudice'>",
        "cache_control": {"type": "ephemeral"}
      }
    ],
    messages=[{"role": "user", "content": "Analyze the major themes in 'Pride and Prejudice'."}],
)
print(response.usage.model_dump_json())

## Call the model again with the same inputs up to the cache checkpoint
response = client.messages.create(.....)
print(response.usage.model_dump_json())
```

```typescript
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic();

const response = await client.messages.create({
  model: "claude-sonnet-4-5",
  max_tokens: 1024,
  system: [
    {
      type: "text",
      text: "You are an AI assistant tasked with analyzing literary works. Your goal is to provide insightful commentary on themes, characters, and writing style.\n",
    },
    {
      type: "text",
      text: "<the entire contents of 'Pride and Prejudice'>",
      cache_control: { type: "ephemeral" }
    }
  ],
  messages: [
    {
      role: "user",
      content: "Analyze the major themes in 'Pride and Prejudice'."
    }
  ]
});
console.log(response.usage);

// Call the model again with the same inputs up to the cache checkpoint
const new_response = await client.messages.create(...)
console.log(new_response.usage);
```

```java
import java.util.List;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.CacheControlEphemeral;
import com.anthropic.models.messages.Message;
import com.anthropic.models.messages.MessageCreateParams;
import com.anthropic.models.messages.Model;
import com.anthropic.models.messages.TextBlockParam;

public class PromptCachingExample {

  public static void main(String[] args) {
    AnthropicClient client = AnthropicOkHttpClient.fromEnv();

    MessageCreateParams params = MessageCreateParams.builder()
        .model(Model.CLAUDE_OPUS_4_20250514)
        .maxTokens(1024)
        .systemOfTextBlockParams(List.of(
            TextBlockParam.builder()
                .text(
                    "You are an AI assistant tasked with analyzing literary works. Your goal is to provide insightful commentary on themes, characters, and writing style.\n")
                .build(),
            TextBlockParam.builder()
                .text("<the entire contents of 'Pride and Prejudice'>")
                .cacheControl(CacheControlEphemeral.builder().build())
                .build()))
        .addUserMessage("Analyze the major themes in 'Pride and Prejudice'.")
        .build();

    Message message = client.messages().create(params);
    System.out.println(message.usage());
  }
}
```

```JSON
{"cache_creation_input_tokens":188086,"cache_read_input_tokens":0,"input_tokens":21,"output_tokens":393}
{"cache_creation_input_tokens":0,"cache_read_input_tokens":188086,"input_tokens":21,"output_tokens":393}
```

In this example, the entire text of "Pride and Prejudice" is cached using the `cache_control` parameter. This enables reuse of this large text across multiple API calls without reprocessing it each time. Changing only the user message allows you to ask various questions about the book while utilizing the cached content, leading to faster responses and improved efficiency.

---

### How prompt caching works

When you send a request with prompt caching enabled:

1. The system checks if a prompt prefix, up to a specified cache breakpoint, is already cached from a recent query.
2. If found, it uses the cached version, reducing processing time and costs.
3. Otherwise, it processes the full prompt and caches the prefix once the response begins.

This is especially useful for:

- Prompts with many examples
- Large amounts of context or background information
- Repetitive tasks with consistent instructions
- Long multi-turn conversations

By default, the cache has a 5-minute lifetime. The cache is refreshed for no additional cost each time the cached content is used.

> [!NOTE]
>
> If you find that 5 minutes is too short, Anthropic also offers a 1-hour cache duration [at additional cost](#pricing). The 1-hour cache is currently in beta.

For more information, see [1-hour cache duration](#1-hour-cache-duration).

> [!TIP]
>
> **Prompt caching caches the full prefix**
>
> Prompt caching references the entire prompt - `tools`, `system`, and `messages` (in that order) up to and including the block designated with `cache_control`.

---

### Pricing

Prompt caching introduces a new pricing structure. The table below shows the price per million tokens for each supported model:

| Model                                                                                             | Base Input Tokens | 5m Cache Writes | 1h Cache Writes | Cache Hits & Refreshes | Output Tokens |
| ------------------------------------------------------------------------------------------------- | ----------------- | --------------- | --------------- | ---------------------- | ------------- |
| Claude Opus 4.1                                                                                   | \$15 / MTok       | \$18.75 / MTok  | \$30 / MTok     | \$1.50 / MTok          | \$75 / MTok   |
| Claude Opus 4                                                                                     | \$15 / MTok       | \$18.75 / MTok  | \$30 / MTok     | \$1.50 / MTok          | \$75 / MTok   |
| Claude Sonnet 4.5                                                                                 | \$3 / MTok        | \$3.75 / MTok   | \$6 / MTok      | \$0.30 / MTok          | \$15 / MTok   |
| Claude Sonnet 4                                                                                   | \$3 / MTok        | \$3.75 / MTok   | \$6 / MTok      | \$0.30 / MTok          | \$15 / MTok   |
| Claude Sonnet 3.7 ([deprecated](https://docs.claude.com/en/docs/about-claude/model-deprecations)) | \$3 / MTok        | \$3.75 / MTok   | \$6 / MTok      | \$0.30 / MTok          | \$15 / MTok   |
| Claude Haiku 4.5                                                                                  | \$1 / MTok        | \$1.25 / MTok   | \$2 / MTok      | \$0.10 / MTok          | \$5 / MTok    |
| Claude Haiku 3.5                                                                                  | \$0.80 / MTok     | \$1 / MTok      | \$1.6 / MTok    | \$0.08 / MTok          | \$4 / MTok    |
| Claude Opus 3 ([deprecated](https://docs.claude.com/en/docs/about-claude/model-deprecations))     | \$15 / MTok       | \$18.75 / MTok  | \$30 / MTok     | \$1.50 / MTok          | \$75 / MTok   |
| Claude Haiku 3                                                                                    | \$0.25 / MTok     | \$0.30 / MTok   | \$0.50 / MTok   | \$0.03 / MTok          | \$1.25 / MTok |

> [!NOTE]
>
> The table above reflects the following pricing multipliers for prompt caching:
>
> - 5-minute cache write tokens are 1.25 times the base input tokens price
> - 1-hour cache write tokens are 2 times the base input tokens price
> - Cache read tokens are 0.1 times the base input tokens price

---

### How to implement prompt caching

#### Supported models

Prompt caching is currently supported on:

- Claude Opus 4.1
- Claude Opus 4
- Claude Sonnet 4.5
- Claude Sonnet 4
- Claude Sonnet 3.7
- Claude Haiku 4.5
- Claude Haiku 3.5
- Claude Haiku 3
- Claude Opus 3 ([deprecated](https://docs.claude.com/en/docs/about-claude/model-deprecations))

#### Structuring your prompt

Place static content (tool definitions, system instructions, context, examples) at the beginning of your prompt. Mark the end of the reusable content for caching using the `cache_control` parameter.

Cache prefixes are created in the following order: `tools`, `system`, then `messages`. This order forms a hierarchy where each level builds upon the previous ones.

##### How automatic prefix checking works

You can use just one cache breakpoint at the end of your static content, and the system will automatically find the longest matching prefix. Understanding how this works helps you optimize your caching strategy.

**Three core principles:**

1. **Cache keys are cumulative**: When you explicitly cache a block with `cache_control`, the cache hash key is generated by hashing all previous blocks in the conversation sequentially. This means the cache for each block depends on all content that came before it.

2. **Backward sequential checking**: The system checks for cache hits by working backwards from your explicit breakpoint, checking each previous block in reverse order. This ensures you get the longest possible cache hit.

3. **20-block lookback window**: The system only checks up to 20 blocks before each explicit `cache_control` breakpoint. After checking 20 blocks without a match, it stops checking and moves to the next explicit breakpoint (if any).

Example: Understanding the lookback window

Consider a conversation with 30 content blocks where you set `cache_control` only on block 30:

- **If you send block 31 with no changes to previous blocks**: The system checks block 30 (match!). You get a cache hit at block 30, and only block 31 needs processing.

- **If you modify block 25 and send block 31**: The system checks backwards from block 30 → 29 → 28... → 25 (no match) → 24 (match!). Since block 24 hasn't changed, you get a cache hit at block 24, and only blocks 25-30 need reprocessing.

- **If you modify block 5 and send block 31**: The system checks backwards from block 30 → 29 → 28... → 11 (check #20). After 20 checks without finding a match, it stops looking. Since block 5 is beyond the 20-block window, no cache hit occurs and all blocks need reprocessing. However, if you had set an explicit `cache_control` breakpoint on block 5, the system would continue checking from that breakpoint: block 5 (no match) → block 4 (match!). This allows a cache hit at block 4, demonstrating why you should place breakpoints before editable content.

**Key takeaway**: Always set an explicit cache breakpoint at the end of your conversation to maximize your chances of cache hits. Additionally, set breakpoints just before content blocks that might be editable to ensure those sections can be cached independently.

##### When to use multiple breakpoints

You can define up to 4 cache breakpoints if you want to:

- Cache different sections that change at different frequencies (e.g., tools rarely change, but context updates daily)
- Have more control over exactly what gets cached
- Ensure caching for content more than 20 blocks before your final breakpoint
- Place breakpoints before editable content to guarantee cache hits even when changes occur beyond the 20-block window

> [!NOTE]
>
> > **Important limitation**: If your prompt has more than 20 content blocks before your cache breakpoint, and you modify content earlier than those 20 blocks, you won't get a cache hit unless you add additional explicit breakpoints closer to that content.

#### Cache limitations

The minimum cacheable prompt length is:

- 1024 tokens for Claude Opus 4.1, Claude Opus 4, Claude Sonnet 4.5, Claude Sonnet 4, Claude Sonnet 3.7 ([deprecated](https://docs.claude.com/en/docs/about-claude/model-deprecations)), and Claude Opus 3 ([deprecated](https://docs.claude.com/en/docs/about-claude/model-deprecations))
- 4096 tokens for Claude Haiku 4.5
- 2048 tokens for Claude Haiku 3.5 and Claude Haiku 3

Shorter prompts cannot be cached, even if marked with `cache_control`. Any requests to cache fewer than this number of tokens will be processed without caching. To see if a prompt was cached, see the response usage [fields](https://docs.claude.com/en/docs/build-with-claude/prompt-caching#tracking-cache-performance).

For concurrent requests, note that a cache entry only becomes available after the first response begins. If you need cache hits for parallel requests, wait for the first response before sending subsequent requests.

Currently, "ephemeral" is the only supported cache type, which by default has a 5-minute lifetime.

#### Understanding cache breakpoint costs

**Cache breakpoints themselves don't add any cost.** You are only charged for:

- **Cache writes**: When new content is written to the cache (25% more than base input tokens for 5-minute TTL)
- **Cache reads**: When cached content is used (10% of base input token price)
- **Regular input tokens**: For any uncached content

Adding more `cache_control` breakpoints doesn't increase your costs - you still pay the same amount based on what content is actually cached and read. The breakpoints simply give you control over what sections can be cached independently.

#### What can be cached

Most blocks in the request can be designated for caching with `cache_control`. This includes:

- Tools: Tool definitions in the `tools` array
- System messages: Content blocks in the `system` array
- Text messages: Content blocks in the `messages.content` array, for both user and assistant turns
- Images & Documents: Content blocks in the `messages.content` array, in user turns
- Tool use and tool results: Content blocks in the `messages.content` array, in both user and assistant turns

Each of these elements can be marked with `cache_control` to enable caching for that portion of the request.

#### What cannot be cached

While most request blocks can be cached, there are some exceptions:

- Thinking blocks cannot be cached directly with `cache_control`. However, thinking blocks CAN be cached alongside other content when they appear in previous assistant turns. When cached this way, they DO count as input tokens when read from cache.
- Sub-content blocks (like [citations](https://docs.claude.com/en/docs/build-with-claude/citations)) themselves cannot be cached directly. Instead, cache the top-level block.

  In the case of citations, the top-level document content blocks that serve as the source material for citations can be cached. This allows you to use prompt caching with citations effectively by caching the documents that citations will reference.

- Empty text blocks cannot be cached.

#### What invalidates the cache

Modifications to cached content can invalidate some or all of the cache.

As described in [Structuring your prompt](#structuring-your-prompt), the cache follows the hierarchy: `tools` → `system` → `messages`. Changes at each level invalidate that level and all subsequent levels.

The following table shows which parts of the cache are invalidated by different types of changes. ✘ indicates that the cache is invalidated, while ✓ indicates that the cache remains valid.

| What changes                                              | Tools cache | System cache | Messages cache | Impact                                                                                                                                                                                                                                                                                                                           |
| --------------------------------------------------------- | ----------- | ------------ | -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Tool definitions**                                      | ✘           | ✘            | ✘              | Modifying tool definitions (names, descriptions, parameters) invalidates the entire cache                                                                                                                                                                                                                                        |
| **Web search toggle**                                     | ✓           | ✘            | ✘              | Enabling/disabling web search modifies the system prompt                                                                                                                                                                                                                                                                         |
| **Citations toggle**                                      | ✓           | ✘            | ✘              | Enabling/disabling citations modifies the system prompt                                                                                                                                                                                                                                                                          |
| **Tool choice**                                           | ✓           | ✓            | ✘              | Changes to `tool_choice` parameter only affect message blocks                                                                                                                                                                                                                                                                    |
| **Images**                                                | ✓           | ✓            | ✘              | Adding/removing images anywhere in the prompt affects message blocks                                                                                                                                                                                                                                                             |
| **Thinking parameters**                                   | ✓           | ✓            | ✘              | Changes to extended thinking settings (enable/disable, budget) affect message blocks                                                                                                                                                                                                                                             |
| **Non-tool results passed to extended thinking requests** | ✓           | ✓            | ✘              | When non-tool results are passed in requests while extended thinking is enabled, all previously-cached thinking blocks are stripped from context, and any messages in context that follow those thinking blocks are removed from the cache. For more details, see [Caching with thinking blocks](#caching-with-thinking-blocks). |

#### Tracking cache performance

Monitor cache performance using these API response fields, within `usage` in the response (or `message_start` event if [streaming](https://docs.claude.com/en/docs/build-with-claude/streaming)):

- `cache_creation_input_tokens`: Number of tokens written to the cache when creating a new entry.
- `cache_read_input_tokens`: Number of tokens retrieved from the cache for this request.
- `input_tokens`: Number of input tokens which were not read from or used to create a cache (i.e., tokens after the last cache breakpoint).

> [!NOTE]
>
> > **Understanding the token breakdown**
>
> The `input_tokens` field represents only the tokens that come **after the last cache breakpoint** in your request - not all the input tokens you sent.
>
> To calculate total input tokens:
>
> ```text
> total_input_tokens = cache_read_input_tokens + cache_creation_input_tokens + input_tokens
> ```
>
> **Spatial explanation:**
>
> - `cache_read_input_tokens` = tokens before breakpoint already cached (reads)
> - `cache_creation_input_tokens` = tokens before breakpoint being cached now (writes)
> - `input_tokens` = tokens after your last breakpoint (not eligible for cache)
>
> **Example:** If you have a request with 100,000 tokens of cached content (read from cache), 0 tokens of new content being cached, and 50 tokens in your user message (after the cache breakpoint):
>
> - `cache_read_input_tokens`: 100,000
> - `cache_creation_input_tokens`: 0
> - `input_tokens`: 50
> - **Total input tokens processed**: 100,050 tokens
>
> This is important for understanding both costs and rate limits, as `input_tokens` will typically be much smaller than your total input when using caching effectively.

#### Best practices for effective caching

To optimize prompt caching performance:

- Cache stable, reusable content like system instructions, background information, large contexts, or frequent tool definitions.
- Place cached content at the prompt's beginning for best performance.
- Use cache breakpoints strategically to separate different cacheable prefix sections.
- Set cache breakpoints at the end of conversations and just before editable content to maximize cache hit rates, especially when working with prompts that have more than 20 content blocks.
- Regularly analyze cache hit rates and adjust your strategy as needed.

#### Optimizing for different use cases

Tailor your prompt caching strategy to your scenario:

- Conversational agents: Reduce cost and latency for extended conversations, especially those with long instructions or uploaded documents.
- Coding assistants: Improve autocomplete and codebase Q\&A by keeping relevant sections or a summarized version of the codebase in the prompt.
- Large document processing: Incorporate complete long-form material including images in your prompt without increasing response latency.
- Detailed instruction sets: Share extensive lists of instructions, procedures, and examples to fine-tune Claude's responses. Developers often include an example or two in the prompt, but with prompt caching you can get even better performance by including 20+ diverse examples of high quality answers.
- Agentic tool use: Enhance performance for scenarios involving multiple tool calls and iterative code changes, where each step typically requires a new API call.
- Talk to books, papers, documentation, podcast transcripts, and other longform content: Bring any knowledge base alive by embedding the entire document(s) into the prompt, and letting users ask it questions.

#### Troubleshooting common issues

If experiencing unexpected behavior:

- Ensure cached sections are identical and marked with cache_control in the same locations across calls
- Check that calls are made within the cache lifetime (5 minutes by default)
- Verify that `tool_choice` and image usage remain consistent between calls
- Validate that you are caching at least the minimum number of tokens
- The system automatically checks for cache hits at previous content block boundaries (up to \~20 blocks before your breakpoint). For prompts with more than 20 content blocks, you may need additional `cache_control` parameters earlier in the prompt to ensure all content can be cached
- Verify that the keys in your `tool_use` content blocks have stable ordering as some languages (e.g. Swift, Go) randomize key order during JSON conversion, breaking caches

> [!NOTE]
>
> Changes to `tool_choice` or the presence/absence of images anywhere in the prompt will invalidate the cache, requiring a new cache entry to be created. For more details on cache invalidation, see [What invalidates the cache](#what-invalidates-the-cache).

#### Caching with thinking blocks

When using [extended thinking](https://docs.claude.com/en/docs/build-with-claude/extended-thinking) with prompt caching, thinking blocks have special behavior:

**Automatic caching alongside other content**: While thinking blocks cannot be explicitly marked with `cache_control`, they get cached as part of the request content when you make subsequent API calls with tool results. This commonly happens during tool use when you pass thinking blocks back to continue the conversation.

**Input token counting**: When thinking blocks are read from cache, they count as input tokens in your usage metrics. This is important for cost calculation and token budgeting.

**Cache invalidation patterns**:

- Cache remains valid when only tool results are provided as user messages
- Cache gets invalidated when non-tool-result user content is added, causing all previous thinking blocks to be stripped
- This caching behavior occurs even without explicit `cache_control` markers

For more details on cache invalidation, see [What invalidates the cache](#what-invalidates-the-cache).

**Example with tool use**:

```text
Request 1: User: "What's the weather in Paris?"
Response: [thinking_block_1] + [tool_use block 1]

Request 2:
User: ["What's the weather in Paris?"],
Assistant: [thinking_block_1] + [tool_use block 1],
User: [tool_result_1, cache=True]
Response: [thinking_block_2] + [text block 2]
## Request 2 caches its request content (not the response)
## The cache includes: user message, thinking_block_1, tool_use block 1, and tool_result_1

Request 3:
User: ["What's the weather in Paris?"],
Assistant: [thinking_block_1] + [tool_use block 1],
User: [tool_result_1, cache=True],
Assistant: [thinking_block_2] + [text block 2],
User: [Text response, cache=True]
## Non-tool-result user block causes all thinking blocks to be ignored
## This request is processed as if thinking blocks were never present
```

When a non-tool-result user block is included, it designates a new assistant loop and all previous thinking blocks are removed from context.

For more detailed information, see the [extended thinking documentation](https://docs.claude.com/en/docs/build-with-claude/extended-thinking#understanding-thinking-block-caching-behavior).

---

### Cache storage and sharing

- **Organization Isolation**: Caches are isolated between organizations. Different organizations never share caches, even if they use identical prompts.

- **Exact Matching**: Cache hits require 100% identical prompt segments, including all text and images up to and including the block marked with cache control.

- **Output Token Generation**: Prompt caching has no effect on output token generation. The response you receive will be identical to what you would get if prompt caching was not used.

---

### 1-hour cache duration

If you find that 5 minutes is too short, Anthropic also offers a 1-hour cache duration [at additional cost](#pricing).

To use the extended cache, include `ttl` in the `cache_control` definition like this:

```JSON
"cache_control": {
    "type": "ephemeral",
    "ttl": "5m" | "1h"
}
```

The response will include detailed cache information like the following:

```JSON
{
    "usage": {
        "input_tokens": ...,
        "cache_read_input_tokens": ...,
        "cache_creation_input_tokens": ...,
        "output_tokens": ...,

        "cache_creation": {
            "ephemeral_5m_input_tokens": 456,
            "ephemeral_1h_input_tokens": 100,
        }
    }
}
```

Note that the current `cache_creation_input_tokens` field equals the sum of the values in the `cache_creation` object.

#### When to use the 1-hour cache

If you have prompts that are used at a regular cadence (i.e., system prompts that are used more frequently than every 5 minutes), continue to use the 5-minute cache, since this will continue to be refreshed at no additional charge.

The 1-hour cache is best used in the following scenarios:

- When you have prompts that are likely used less frequently than 5 minutes, but more frequently than every hour. For example, when an agentic side-agent will take longer than 5 minutes, or when storing a long chat conversation with a user and you generally expect that user may not respond in the next 5 minutes.
- When latency is important and your follow up prompts may be sent beyond 5 minutes.
- When you want to improve your rate limit utilization, since cache hits are not deducted against your rate limit.

> [!NOTE]
>
> The 5-minute and 1-hour cache behave the same with respect to latency. You will generally see improved time-to-first-token for long documents.

#### Mixing different TTLs

You can use both 1-hour and 5-minute cache controls in the same request, but with an important constraint: Cache entries with longer TTL must appear before shorter TTLs (i.e., a 1-hour cache entry must appear before any 5-minute cache entries).

When mixing TTLs, we determine three billing locations in your prompt:

1. Position `A`: The token count at the highest cache hit (or 0 if no hits).
2. Position `B`: The token count at the highest 1-hour `cache_control` block after `A` (or equals `A` if none exist).
3. Position `C`: The token count at the last `cache_control` block.

> [!NOTE]
>
> If `B` and/or `C` are larger than `A`, they will necessarily be cache misses, because `A` is the highest cache hit.

You'll be charged for:

1. Cache read tokens for `A`.
2. 1-hour cache write tokens for `(B - A)`.
3. 5-minute cache write tokens for `(C - B)`.

Here are 3 examples. This depicts the input tokens of 3 requests, each of which has different cache hits and cache misses. Each has a different calculated pricing, shown in the colored boxes, as a result. <img src="https://mintcdn.com/anthropic-claude-docs/LF5WV0SNF6oudpT5/images/prompt-cache-mixed-ttl.svg?fit=max&auto=format&n=LF5WV0SNF6oudpT5&q=85&s=10a8997695f0f78953fdac300a3373e9" alt="Mixing TTLs Diagram" data-og-width="1376" width="1376" data-og-height="976" height="976" data-path="images/prompt-cache-mixed-ttl.svg" data-optimize="true" data-opv="3" srcset="https://mintcdn.com/anthropic-claude-docs/LF5WV0SNF6oudpT5/images/prompt-cache-mixed-ttl.svg?w=280&fit=max&auto=format&n=LF5WV0SNF6oudpT5&q=85&s=7a8de34e52bbf67c60b2eeda57690ea3 280w, https://mintcdn.com/anthropic-claude-docs/LF5WV0SNF6oudpT5/images/prompt-cache-mixed-ttl.svg?w=560&fit=max&auto=format&n=LF5WV0SNF6oudpT5&q=85&s=cdc3a1950dc88fbfb5679320df656ef2 560w, https://mintcdn.com/anthropic-claude-docs/LF5WV0SNF6oudpT5/images/prompt-cache-mixed-ttl.svg?w=840&fit=max&auto=format&n=LF5WV0SNF6oudpT5&q=85&s=0df34408f5ec905ade69060ac8b5077b 840w, https://mintcdn.com/anthropic-claude-docs/LF5WV0SNF6oudpT5/images/prompt-cache-mixed-ttl.svg?w=1100&fit=max&auto=format&n=LF5WV0SNF6oudpT5&q=85&s=0c434f1b04d12e6a0a20cfe58b22d4e5 1100w, https://mintcdn.com/anthropic-claude-docs/LF5WV0SNF6oudpT5/images/prompt-cache-mixed-ttl.svg?w=1650&fit=max&auto=format&n=LF5WV0SNF6oudpT5&q=85&s=c800577f55f6e3383e3807644a5e0743 1650w, https://mintcdn.com/anthropic-claude-docs/LF5WV0SNF6oudpT5/images/prompt-cache-mixed-ttl.svg?w=2500&fit=max&auto=format&n=LF5WV0SNF6oudpT5&q=85&s=7e7079d06a969ea814980f4e570d2fa2 2500w" />

---

### Prompt caching examples

To help you get started with prompt caching, we've prepared a [prompt caching cookbook](https://github.com/anthropics/anthropic-cookbook/blob/main/misc/prompt_caching.ipynb) with detailed examples and best practices.

Below, we've included several code snippets that showcase various prompt caching patterns. These examples demonstrate how to implement caching in different scenarios, helping you understand the practical applications of this feature:

```bash
curl https://api.anthropic.com/v1/messages \
    --header "x-api-key: $ANTHROPIC_API_KEY" \
    --header "anthropic-version: 2023-06-01" \
    --header "content-type: application/json" \
    --data \
    '{
        "model": "claude-sonnet-4-5",
        "max_tokens": 1024,
        "system": [
            {
                "type": "text",
                "text": "You are an AI assistant tasked with analyzing legal documents."
            },
            {
                "type": "text",
                "text": "Here is the full text of a complex legal agreement: [Insert full text of a 50-page legal agreement here]",
                "cache_control": {"type": "ephemeral"}
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": "What are the key terms and conditions in this agreement?"
            }
        ]
    }'
```

```Python
import anthropic
client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "You are an AI assistant tasked with analyzing legal documents."
        },
        {
            "type": "text",
            "text": "Here is the full text of a complex legal agreement: [Insert full text of a 50-page legal agreement here]",
            "cache_control": {"type": "ephemeral"}
        }
    ],
    messages=[
        {
            "role": "user",
            "content": "What are the key terms and conditions in this agreement?"
        }
    ]
)
print(response.model_dump_json())
```

```typescript
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic();

const response = await client.messages.create({
	model: 'claude-sonnet-4-5',
	max_tokens: 1024,
	system: [
		{
			type: 'text',
			text: 'You are an AI assistant tasked with analyzing legal documents.',
		},
		{
			type: 'text',
			text: 'Here is the full text of a complex legal agreement: [Insert full text of a 50-page legal agreement here]',
			cache_control: { type: 'ephemeral' },
		},
	],
	messages: [
		{
			role: 'user',
			content: 'What are the key terms and conditions in this agreement?',
		},
	],
});
console.log(response);
```

```java
import java.util.List;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.CacheControlEphemeral;
import com.anthropic.models.messages.Message;
import com.anthropic.models.messages.MessageCreateParams;
import com.anthropic.models.messages.Model;
import com.anthropic.models.messages.TextBlockParam;

public class LegalDocumentAnalysisExample {

  public static void main(String[] args) {
    AnthropicClient client = AnthropicOkHttpClient.fromEnv();

    MessageCreateParams params = MessageCreateParams.builder()
        .model(Model.CLAUDE_OPUS_4_20250514)
        .maxTokens(1024)
        .systemOfTextBlockParams(List.of(
            TextBlockParam.builder()
                .text("You are an AI assistant tasked with analyzing legal documents.")
                .build(),
            TextBlockParam.builder()
                .text(
                    "Here is the full text of a complex legal agreement: [Insert full text of a 50-page legal agreement here]")
                .cacheControl(CacheControlEphemeral.builder().build())
                .build()))
        .addUserMessage("What are the key terms and conditions in this agreement?")
        .build();

    Message message = client.messages().create(params);
    System.out.println(message);
  }
}
```

This example demonstrates basic prompt caching usage, caching the full text of the legal agreement as a prefix while keeping the user instruction uncached.

For the first request:

- `input_tokens`: Number of tokens in the user message only
- `cache_creation_input_tokens`: Number of tokens in the entire system message, including the legal document
- `cache_read_input_tokens`: 0 (no cache hit on first request)

For subsequent requests within the cache lifetime:

- `input_tokens`: Number of tokens in the user message only
- `cache_creation_input_tokens`: 0 (no new cache creation)
- `cache_read_input_tokens`: Number of tokens in the entire cached system message

```bash
curl https://api.anthropic.com/v1/messages \
    --header "x-api-key: $ANTHROPIC_API_KEY" \
    --header "anthropic-version: 2023-06-01" \
    --header "content-type: application/json" \
    --data \
    '{
        "model": "claude-sonnet-4-5",
        "max_tokens": 1024,
        "tools": [
            {
                "name": "get_weather",
                "description": "Get the current weather in a given location",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA"
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "The unit of temperature, either celsius or fahrenheit"
                        }
                    },
                    "required": ["location"]
                }
            },
            # many more tools
            {
                "name": "get_time",
                "description": "Get the current time in a given time zone",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "timezone": {
                            "type": "string",
                            "description": "The IANA time zone name, e.g. America/Los_Angeles"
                        }
                    },
                    "required": ["timezone"]
                },
                "cache_control": {"type": "ephemeral"}
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": "What is the weather and time in New York?"
            }
        ]
    }'
```

```Python
import anthropic
client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    tools=[
        {
            "name": "get_weather",
            "description": "Get the current weather in a given location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "The unit of temperature, either 'celsius' or 'fahrenheit'"
                    }
                },
                "required": ["location"]
            },
        },
        # many more tools
        {
            "name": "get_time",
            "description": "Get the current time in a given time zone",
            "input_schema": {
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "The IANA time zone name, e.g. America/Los_Angeles"
                    }
                },
                "required": ["timezone"]
            },
            "cache_control": {"type": "ephemeral"}
        }
    ],
    messages=[
        {
            "role": "user",
            "content": "What's the weather and time in New York?"
        }
    ]
)
print(response.model_dump_json())
```

```typescript
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic();

const response = await client.messages.create({
	model: 'claude-sonnet-4-5',
	max_tokens: 1024,
	tools = [
		{
			name: 'get_weather',
			description: 'Get the current weather in a given location',
			input_schema: {
				type: 'object',
				properties: {
					location: {
						type: 'string',
						description: 'The city and state, e.g. San Francisco, CA',
					},
					unit: {
						type: 'string',
						enum: ['celsius', 'fahrenheit'],
						description: "The unit of temperature, either 'celsius' or 'fahrenheit'",
					},
				},
				required: ['location'],
			},
		},
		// many more tools
		{
			name: 'get_time',
			description: 'Get the current time in a given time zone',
			input_schema: {
				type: 'object',
				properties: {
					timezone: {
						type: 'string',
						description: 'The IANA time zone name, e.g. America/Los_Angeles',
					},
				},
				required: ['timezone'],
			},
			cache_control: { type: 'ephemeral' },
		},
	],
	messages: [
		{
			role: 'user',
			content: "What's the weather and time in New York?",
		},
	],
});
console.log(response);
```

```java
import java.util.List;
import java.util.Map;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.core.JsonValue;
import com.anthropic.models.messages.CacheControlEphemeral;
import com.anthropic.models.messages.Message;
import com.anthropic.models.messages.MessageCreateParams;
import com.anthropic.models.messages.Model;
import com.anthropic.models.messages.Tool;
import com.anthropic.models.messages.Tool.InputSchema;

public class ToolsWithCacheControlExample {

  public static void main(String[] args) {
    AnthropicClient client = AnthropicOkHttpClient.fromEnv();

    // Weather tool schema
    InputSchema weatherSchema = InputSchema.builder()
        .properties(JsonValue.from(Map.of(
            "location", Map.of(
                "type", "string",
                "description", "The city and state, e.g. San Francisco, CA"),
            "unit", Map.of(
                "type", "string",
                "enum", List.of("celsius", "fahrenheit"),
                "description", "The unit of temperature, either celsius or fahrenheit"))))
        .putAdditionalProperty("required", JsonValue.from(List.of("location")))
        .build();

    // Time tool schema
    InputSchema timeSchema = InputSchema.builder()
        .properties(JsonValue.from(Map.of(
            "timezone", Map.of(
                "type", "string",
                "description", "The IANA time zone name, e.g. America/Los_Angeles"))))
        .putAdditionalProperty("required", JsonValue.from(List.of("timezone")))
        .build();

    MessageCreateParams params = MessageCreateParams.builder()
        .model(Model.CLAUDE_OPUS_4_20250514)
        .maxTokens(1024)
        .addTool(Tool.builder()
            .name("get_weather")
            .description("Get the current weather in a given location")
            .inputSchema(weatherSchema)
            .build())
        .addTool(Tool.builder()
            .name("get_time")
            .description("Get the current time in a given time zone")
            .inputSchema(timeSchema)
            .cacheControl(CacheControlEphemeral.builder().build())
            .build())
        .addUserMessage("What is the weather and time in New York?")
        .build();

    Message message = client.messages().create(params);
    System.out.println(message);
  }
}
```

In this example, we demonstrate caching tool definitions.

The `cache_control` parameter is placed on the final tool (`get_time`) to designate all of the tools as part of the static prefix.

This means that all tool definitions, including `get_weather` and any other tools defined before `get_time`, will be cached as a single prefix.

This approach is useful when you have a consistent set of tools that you want to reuse across multiple requests without re-processing them each time.

For the first request:

- `input_tokens`: Number of tokens in the user message
- `cache_creation_input_tokens`: Number of tokens in all tool definitions and system prompt
- `cache_read_input_tokens`: 0 (no cache hit on first request)

For subsequent requests within the cache lifetime:

- `input_tokens`: Number of tokens in the user message
- `cache_creation_input_tokens`: 0 (no new cache creation)
- `cache_read_input_tokens`: Number of tokens in all cached tool definitions and system prompt

```bash
curl https://api.anthropic.com/v1/messages \
    --header "x-api-key: $ANTHROPIC_API_KEY" \
    --header "anthropic-version: 2023-06-01" \
    --header "content-type: application/json" \
    --data \
    '{
        "model": "claude-sonnet-4-5",
        "max_tokens": 1024,
        "system": [
            {
                "type": "text",
                "text": "...long system prompt",
                "cache_control": {"type": "ephemeral"}
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Hello, can you tell me more about the solar system?",
                    }
                ]
            },
            {
                "role": "assistant",
                "content": "Certainly! The solar system is the collection of celestial bodies that orbit our Sun. It consists of eight planets, numerous moons, asteroids, comets, and other objects. The planets, in order from closest to farthest from the Sun, are: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and Neptune. Each planet has its own unique characteristics and features. Is there a specific aspect of the solar system you would like to know more about?"
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Good to know."
                    },
                    {
                        "type": "text",
                        "text": "Tell me more about Mars.",
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
            }
        ]
    }'
```

```Python
import anthropic
client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "...long system prompt",
            "cache_control": {"type": "ephemeral"}
        }
    ],
    messages=[
        # ...long conversation so far
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Hello, can you tell me more about the solar system?",
                }
            ]
        },
        {
            "role": "assistant",
            "content": "Certainly! The solar system is the collection of celestial bodies that orbit our Sun. It consists of eight planets, numerous moons, asteroids, comets, and other objects. The planets, in order from closest to farthest from the Sun, are: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and Neptune. Each planet has its own unique characteristics and features. Is there a specific aspect of the solar system you'd like to know more about?"
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Good to know."
                },
                {
                    "type": "text",
                    "text": "Tell me more about Mars.",
                    "cache_control": {"type": "ephemeral"}
                }
            ]
        }
    ]
)
print(response.model_dump_json())
```

```typescript
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic();

const response = await client.messages.create({
	model: 'claude-sonnet-4-5',
	max_tokens: 1024,
	system = [
		{
			type: 'text',
			text: '...long system prompt',
			cache_control: { type: 'ephemeral' },
		},
	],
	messages = [
		// ...long conversation so far
		{
			role: 'user',
			content: [
				{
					type: 'text',
					text: 'Hello, can you tell me more about the solar system?',
				},
			],
		},
		{
			role: 'assistant',
			content: "Certainly! The solar system is the collection of celestial bodies that orbit our Sun. It consists of eight planets, numerous moons, asteroids, comets, and other objects. The planets, in order from closest to farthest from the Sun, are: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and Neptune. Each planet has its own unique characteristics and features. Is there a specific aspect of the solar system you'd like to know more about?",
		},
		{
			role: 'user',
			content: [
				{
					type: 'text',
					text: 'Good to know.',
				},
				{
					type: 'text',
					text: 'Tell me more about Mars.',
					cache_control: { type: 'ephemeral' },
				},
			],
		},
	],
});
console.log(response);
```

```java
import java.util.List;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.CacheControlEphemeral;
import com.anthropic.models.messages.ContentBlockParam;
import com.anthropic.models.messages.Message;
import com.anthropic.models.messages.MessageCreateParams;
import com.anthropic.models.messages.Model;
import com.anthropic.models.messages.TextBlockParam;

public class ConversationWithCacheControlExample {

  public static void main(String[] args) {
    AnthropicClient client = AnthropicOkHttpClient.fromEnv();

    // Create ephemeral system prompt
    TextBlockParam systemPrompt = TextBlockParam.builder()
        .text("...long system prompt")
        .cacheControl(CacheControlEphemeral.builder().build())
        .build();

    // Create message params
    MessageCreateParams params = MessageCreateParams.builder()
        .model(Model.CLAUDE_OPUS_4_20250514)
        .maxTokens(1024)
        .systemOfTextBlockParams(List.of(systemPrompt))
        // First user message (without cache control)
        .addUserMessage("Hello, can you tell me more about the solar system?")
        // Assistant response
        .addAssistantMessage(
            "Certainly! The solar system is the collection of celestial bodies that orbit our Sun. It consists of eight planets, numerous moons, asteroids, comets, and other objects. The planets, in order from closest to farthest from the Sun, are: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and Neptune. Each planet has its own unique characteristics and features. Is there a specific aspect of the solar system you would like to know more about?")
        // Second user message (with cache control)
        .addUserMessageOfBlockParams(List.of(
            ContentBlockParam.ofText(TextBlockParam.builder()
                .text("Good to know.")
                .build()),
            ContentBlockParam.ofText(TextBlockParam.builder()
                .text("Tell me more about Mars.")
                .cacheControl(CacheControlEphemeral.builder().build())
                .build())))
        .build();

    Message message = client.messages().create(params);
    System.out.println(message);
  }
}
```

In this example, we demonstrate how to use prompt caching in a multi-turn conversation.

During each turn, we mark the final block of the final message with `cache_control` so the conversation can be incrementally cached. The system will automatically lookup and use the longest previously cached prefix for follow-up messages. That is, blocks that were previously marked with a `cache_control` block are later not marked with this, but they will still be considered a cache hit (and also a cache refresh!) if they are hit within 5 minutes.

In addition, note that the `cache_control` parameter is placed on the system message. This is to ensure that if this gets evicted from the cache (after not being used for more than 5 minutes), it will get added back to the cache on the next request.

This approach is useful for maintaining context in ongoing conversations without repeatedly processing the same information.

When this is set up properly, you should see the following in the usage response of each request:

- `input_tokens`: Number of tokens in the new user message (will be minimal)
- `cache_creation_input_tokens`: Number of tokens in the new assistant and user turns
- `cache_read_input_tokens`: Number of tokens in the conversation up to the previous turn

```bash
curl https://api.anthropic.com/v1/messages \
    --header "x-api-key: $ANTHROPIC_API_KEY" \
    --header "anthropic-version: 2023-06-01" \
    --header "content-type: application/json" \
    --data \
    '{
        "model": "claude-sonnet-4-5",
        "max_tokens": 1024,
        "tools": [
            {
                "name": "search_documents",
                "description": "Search through the knowledge base",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_document",
                "description": "Retrieve a specific document by ID",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "doc_id": {
                            "type": "string",
                            "description": "Document ID"
                        }
                    },
                    "required": ["doc_id"]
                },
                "cache_control": {"type": "ephemeral"}
            }
        ],
        "system": [
            {
                "type": "text",
                "text": "You are a helpful research assistant with access to a document knowledge base.\n\n# Instructions\n- Always search for relevant documents before answering\n- Provide citations for your sources\n- Be objective and accurate in your responses\n- If multiple documents contain relevant information, synthesize them\n- Acknowledge when information is not available in the knowledge base",
                "cache_control": {"type": "ephemeral"}
            },
            {
                "type": "text",
                "text": "# Knowledge Base Context\n\nHere are the relevant documents for this conversation:\n\n## Document 1: Solar System Overview\nThe solar system consists of the Sun and all objects that orbit it...\n\n## Document 2: Planetary Characteristics\nEach planet has unique features. Mercury is the smallest planet...\n\n## Document 3: Mars Exploration\nMars has been a target of exploration for decades...\n\n[Additional documents...]",
                "cache_control": {"type": "ephemeral"}
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": "Can you search for information about Mars rovers?"
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tool_1",
                        "name": "search_documents",
                        "input": {"query": "Mars rovers"}
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tool_1",
                        "content": "Found 3 relevant documents: Document 3 (Mars Exploration), Document 7 (Rover Technology), Document 9 (Mission History)"
                    }
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "I found 3 relevant documents about Mars rovers. Let me get more details from the Mars Exploration document."
                    }
                ]
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Yes, please tell me about the Perseverance rover specifically.",
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
            }
        ]
    }'
```

```Python
import anthropic
client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    tools=[
        {
            "name": "search_documents",
            "description": "Search through the knowledge base",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "get_document",
            "description": "Retrieve a specific document by ID",
            "input_schema": {
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "Document ID"
                    }
                },
                "required": ["doc_id"]
            },
            "cache_control": {"type": "ephemeral"}
        }
    ],
    system=[
        {
            "type": "text",
            "text": "You are a helpful research assistant with access to a document knowledge base.\n\n# Instructions\n- Always search for relevant documents before answering\n- Provide citations for your sources\n- Be objective and accurate in your responses\n- If multiple documents contain relevant information, synthesize them\n- Acknowledge when information is not available in the knowledge base",
            "cache_control": {"type": "ephemeral"}
        },
        {
            "type": "text",
            "text": "# Knowledge Base Context\n\nHere are the relevant documents for this conversation:\n\n## Document 1: Solar System Overview\nThe solar system consists of the Sun and all objects that orbit it...\n\n## Document 2: Planetary Characteristics\nEach planet has unique features. Mercury is the smallest planet...\n\n## Document 3: Mars Exploration\nMars has been a target of exploration for decades...\n\n[Additional documents...]",
            "cache_control": {"type": "ephemeral"}
        }
    ],
    messages=[
        {
            "role": "user",
            "content": "Can you search for information about Mars rovers?"
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "tool_1",
                    "name": "search_documents",
                    "input": {"query": "Mars rovers"}
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "tool_1",
                    "content": "Found 3 relevant documents: Document 3 (Mars Exploration), Document 7 (Rover Technology), Document 9 (Mission History)"
                }
            ]
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": "I found 3 relevant documents about Mars rovers. Let me get more details from the Mars Exploration document."
                }
            ]
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Yes, please tell me about the Perseverance rover specifically.",
                    "cache_control": {"type": "ephemeral"}
                }
            ]
        }
    ]
)
print(response.model_dump_json())
```

```typescript
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic();

const response = await client.messages.create({
	model: 'claude-sonnet-4-5',
	max_tokens: 1024,
	tools: [
		{
			name: 'search_documents',
			description: 'Search through the knowledge base',
			input_schema: {
				type: 'object',
				properties: {
					query: {
						type: 'string',
						description: 'Search query',
					},
				},
				required: ['query'],
			},
		},
		{
			name: 'get_document',
			description: 'Retrieve a specific document by ID',
			input_schema: {
				type: 'object',
				properties: {
					doc_id: {
						type: 'string',
						description: 'Document ID',
					},
				},
				required: ['doc_id'],
			},
			cache_control: { type: 'ephemeral' },
		},
	],
	system: [
		{
			type: 'text',
			text: 'You are a helpful research assistant with access to a document knowledge base.\n\n# Instructions\n- Always search for relevant documents before answering\n- Provide citations for your sources\n- Be objective and accurate in your responses\n- If multiple documents contain relevant information, synthesize them\n- Acknowledge when information is not available in the knowledge base',
			cache_control: { type: 'ephemeral' },
		},
		{
			type: 'text',
			text: '# Knowledge Base Context\n\nHere are the relevant documents for this conversation:\n\n## Document 1: Solar System Overview\nThe solar system consists of the Sun and all objects that orbit it...\n\n## Document 2: Planetary Characteristics\nEach planet has unique features. Mercury is the smallest planet...\n\n## Document 3: Mars Exploration\nMars has been a target of exploration for decades...\n\n[Additional documents...]',
			cache_control: { type: 'ephemeral' },
		},
	],
	messages: [
		{
			role: 'user',
			content: 'Can you search for information about Mars rovers?',
		},
		{
			role: 'assistant',
			content: [
				{
					type: 'tool_use',
					id: 'tool_1',
					name: 'search_documents',
					input: { query: 'Mars rovers' },
				},
			],
		},
		{
			role: 'user',
			content: [
				{
					type: 'tool_result',
					tool_use_id: 'tool_1',
					content: 'Found 3 relevant documents: Document 3 (Mars Exploration), Document 7 (Rover Technology), Document 9 (Mission History)',
				},
			],
		},
		{
			role: 'assistant',
			content: [
				{
					type: 'text',
					text: 'I found 3 relevant documents about Mars rovers. Let me get more details from the Mars Exploration document.',
				},
			],
		},
		{
			role: 'user',
			content: [
				{
					type: 'text',
					text: 'Yes, please tell me about the Perseverance rover specifically.',
					cache_control: { type: 'ephemeral' },
				},
			],
		},
	],
});
console.log(response);
```

```java
import java.util.List;
import java.util.Map;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.core.JsonValue;
import com.anthropic.models.messages.CacheControlEphemeral;
import com.anthropic.models.messages.ContentBlockParam;
import com.anthropic.models.messages.Message;
import com.anthropic.models.messages.MessageCreateParams;
import com.anthropic.models.messages.Model;
import com.anthropic.models.messages.TextBlockParam;
import com.anthropic.models.messages.Tool;
import com.anthropic.models.messages.Tool.InputSchema;
import com.anthropic.models.messages.ToolResultBlockParam;
import com.anthropic.models.messages.ToolUseBlockParam;

public class MultipleCacheBreakpointsExample {

  public static void main(String[] args) {
    AnthropicClient client = AnthropicOkHttpClient.fromEnv();

    // Search tool schema
    InputSchema searchSchema = InputSchema.builder()
        .properties(JsonValue.from(Map.of(
            "query", Map.of(
                "type", "string",
                "description", "Search query"))))
        .putAdditionalProperty("required", JsonValue.from(List.of("query")))
        .build();

    // Get document tool schema
    InputSchema getDocSchema = InputSchema.builder()
        .properties(JsonValue.from(Map.of(
            "doc_id", Map.of(
                "type", "string",
                "description", "Document ID"))))
        .putAdditionalProperty("required", JsonValue.from(List.of("doc_id")))
        .build();

    MessageCreateParams params = MessageCreateParams.builder()
        .model(Model.CLAUDE_OPUS_4_20250514)
        .maxTokens(1024)
        // Tools with cache control on the last one
        .addTool(Tool.builder()
            .name("search_documents")
            .description("Search through the knowledge base")
            .inputSchema(searchSchema)
            .build())
        .addTool(Tool.builder()
            .name("get_document")
            .description("Retrieve a specific document by ID")
            .inputSchema(getDocSchema)
            .cacheControl(CacheControlEphemeral.builder().build())
            .build())
        // System prompts with cache control on instructions and context separately
        .systemOfTextBlockParams(List.of(
            TextBlockParam.builder()
                .text(
                    "You are a helpful research assistant with access to a document knowledge base.\n\n# Instructions\n- Always search for relevant documents before answering\n- Provide citations for your sources\n- Be objective and accurate in your responses\n- If multiple documents contain relevant information, synthesize them\n- Acknowledge when information is not available in the knowledge base")
                .cacheControl(CacheControlEphemeral.builder().build())
                .build(),
            TextBlockParam.builder()
                .text(
                    "# Knowledge Base Context\n\nHere are the relevant documents for this conversation:\n\n## Document 1: Solar System Overview\nThe solar system consists of the Sun and all objects that orbit it...\n\n## Document 2: Planetary Characteristics\nEach planet has unique features. Mercury is the smallest planet...\n\n## Document 3: Mars Exploration\nMars has been a target of exploration for decades...\n\n[Additional documents...]")
                .cacheControl(CacheControlEphemeral.builder().build())
                .build()))
        // Conversation history
        .addUserMessage("Can you search for information about Mars rovers?")
        .addAssistantMessageOfBlockParams(List.of(
            ContentBlockParam.ofToolUse(ToolUseBlockParam.builder()
                .id("tool_1")
                .name("search_documents")
                .input(JsonValue.from(Map.of("query", "Mars rovers")))
                .build())))
        .addUserMessageOfBlockParams(List.of(
            ContentBlockParam.ofToolResult(ToolResultBlockParam.builder()
                .toolUseId("tool_1")
                .content(
                    "Found 3 relevant documents: Document 3 (Mars Exploration), Document 7 (Rover Technology), Document 9 (Mission History)")
                .build())))
        .addAssistantMessageOfBlockParams(List.of(
            ContentBlockParam.ofText(TextBlockParam.builder()
                .text(
                    "I found 3 relevant documents about Mars rovers. Let me get more details from the Mars Exploration document.")
                .build())))
        .addUserMessageOfBlockParams(List.of(
            ContentBlockParam.ofText(TextBlockParam.builder()
                .text("Yes, please tell me about the Perseverance rover specifically.")
                .cacheControl(CacheControlEphemeral.builder().build())
                .build())))
        .build();

    Message message = client.messages().create(params);
    System.out.println(message);
  }
}
```

This comprehensive example demonstrates how to use all 4 available cache breakpoints to optimize different parts of your prompt:

1. **Tools cache** (cache breakpoint 1): The `cache_control` parameter on the last tool definition caches all tool definitions.

2. **Reusable instructions cache** (cache breakpoint 2): The static instructions in the system prompt are cached separately. These instructions rarely change between requests.

3. **RAG context cache** (cache breakpoint 3): The knowledge base documents are cached independently, allowing you to update the RAG documents without invalidating the tools or instructions cache.

4. **Conversation history cache** (cache breakpoint 4): The assistant's response is marked with `cache_control` to enable incremental caching of the conversation as it progresses.

This approach provides maximum flexibility:

- If you only update the final user message, all four cache segments are reused
- If you update the RAG documents but keep the same tools and instructions, the first two cache segments are reused
- If you change the conversation but keep the same tools, instructions, and documents, the first three segments are reused
- Each cache breakpoint can be invalidated independently based on what changes in your application

For the first request:

- `input_tokens`: Tokens in the final user message
- `cache_creation_input_tokens`: Tokens in all cached segments (tools + instructions + RAG documents + conversation history)
- `cache_read_input_tokens`: 0 (no cache hits)

For subsequent requests with only a new user message:

- `input_tokens`: Tokens in the new user message only
- `cache_creation_input_tokens`: Any new tokens added to conversation history
- `cache_read_input_tokens`: All previously cached tokens (tools + instructions + RAG documents + previous conversation)

This pattern is especially powerful for:

- RAG applications with large document contexts
- Agent systems that use multiple tools
- Long-running conversations that need to maintain context
- Applications that need to optimize different parts of the prompt independently

---

### FAQ

**In most cases, a single cache breakpoint at the end of your static content is sufficient.** The system automatically checks for cache hits at all previous content block boundaries (up to 20 blocks before your breakpoint) and uses the longest matching prefix.

You only need multiple breakpoints if:

- You have more than 20 content blocks before your desired cache point
- You want to cache sections that update at different frequencies independently
- You need explicit control over what gets cached for cost optimization

Example: If you have system instructions (rarely change) and RAG context (changes daily), you might use two breakpoints to cache them separately.

No, cache breakpoints themselves are free. You only pay for:

- Writing content to cache (25% more than base input tokens for 5-minute TTL)
- Reading from cache (10% of base input token price)
- Regular input tokens for uncached content

The number of breakpoints doesn't affect pricing - only the amount of content cached and read matters.

The usage response includes three separate input token fields that together represent your total input:

```text
total_input_tokens = cache_read_input_tokens + cache_creation_input_tokens + input_tokens
```

- `cache_read_input_tokens`: Tokens retrieved from cache (everything before cache breakpoints that was cached)
- `cache_creation_input_tokens`: New tokens being written to cache (at cache breakpoints)
- `input_tokens`: Tokens **after the last cache breakpoint** that aren't cached

**Important:** `input_tokens` does NOT represent all input tokens - only the portion after your last cache breakpoint. If you have cached content, `input_tokens` will typically be much smaller than your total input.

**Example:** With a 200K token document cached and a 50 token user question:

- `cache_read_input_tokens`: 200,000
- `cache_creation_input_tokens`: 0
- `input_tokens`: 50
- **Total**: 200,050 tokens

This breakdown is critical for understanding both your costs and rate limit usage. See [Tracking cache performance](#tracking-cache-performance) for more details.

The cache's default minimum lifetime (TTL) is 5 minutes. This lifetime is refreshed each time the cached content is used.

If you find that 5 minutes is too short, Anthropic also offers a [1-hour cache TTL](#1-hour-cache-duration).

You can define up to 4 cache breakpoints (using `cache_control` parameters) in your prompt.

No, prompt caching is currently only available for Claude Opus 4.1, Claude Opus 4, Claude Sonnet 4.5, Claude Sonnet 4, Claude Sonnet 3.7, Claude Haiku 4.5, Claude Haiku 3.5, Claude Haiku 3, and Claude Opus 3 ([deprecated](https://docs.claude.com/en/docs/about-claude/model-deprecations)).

Cached system prompts and tools will be reused when thinking parameters change. However, thinking changes (enabling/disabling or budget changes) will invalidate previously cached prompt prefixes with messages content.

For more details on cache invalidation, see [What invalidates the cache](#what-invalidates-the-cache).

For more on extended thinking, including its interaction with tool use and prompt caching, see the [extended thinking documentation](https://docs.claude.com/en/docs/build-with-claude/extended-thinking#extended-thinking-and-prompt-caching).

To enable prompt caching, include at least one `cache_control` breakpoint in your API request.

Yes, prompt caching can be used alongside other API features like tool use and vision capabilities. However, changing whether there are images in a prompt or modifying tool use settings will break the cache.

For more details on cache invalidation, see [What invalidates the cache](#what-invalidates-the-cache).

Prompt caching introduces a new pricing structure where cache writes cost 25% more than base input tokens, while cache hits cost only 10% of the base input token price.

Currently, there's no way to manually clear the cache. Cached prefixes automatically expire after a minimum of 5 minutes of inactivity.

You can monitor cache performance using the `cache_creation_input_tokens` and `cache_read_input_tokens` fields in the API response.

See [What invalidates the cache](#what-invalidates-the-cache) for more details on cache invalidation, including a list of changes that require creating a new cache entry.

Prompt caching is designed with strong privacy and data separation measures:

1. Cache keys are generated using a cryptographic hash of the prompts up to the cache control point. This means only requests with identical prompts can access a specific cache.

2. Caches are organization-specific. Users within the same organization can access the same cache if they use identical prompts, but caches are not shared across different organizations, even for identical prompts.

3. The caching mechanism is designed to maintain the integrity and privacy of each unique conversation or context.

4. It's safe to use `cache_control` anywhere in your prompts. For cost efficiency, it's better to exclude highly variable parts (e.g., user's arbitrary input) from caching.

These measures ensure that prompt caching maintains data privacy and security while offering performance benefits.

Yes, it is possible to use prompt caching with your [Batches API](https://docs.claude.com/en/docs/build-with-claude/batch-processing) requests. However, because asynchronous batch requests can be processed concurrently and in any order, cache hits are provided on a best-effort basis.

The [1-hour cache](#1-hour-cache-duration) can help improve your cache hits. The most cost effective way of using it is the following:

- Gather a set of message requests that have a shared prefix.
- Send a batch request with just a single request that has this shared prefix and a 1-hour cache block. This will get written to the 1-hour cache.
- As soon as this is complete, submit the rest of the requests. You will have to monitor the job to know when it completes.

This is typically better than using the 5-minute cache simply because it’s common for batch requests to take between 5 minutes and 1 hour to complete. We’re considering ways to improve these cache hit rates and making this process more straightforward.

This error typically appears when you have upgraded your SDK or you are using outdated code examples. Prompt caching is now generally available, so you no longer need the beta prefix. Instead of:

```Python
python client.beta.prompt_caching.messages.create(...)
```

Simply use:

```Python
python client.messages.create(...)
```

This error typically appears when you have upgraded your SDK or you are using outdated code examples. Prompt caching is now generally available, so you no longer need the beta prefix. Instead of:

```typescript
client.beta.promptCaching.messages.create(...)
```

Simply use:

```typescript
client.messages.create(...)
```

---

## [Token counting](https://docs.claude.com/en/docs/build-with-claude/token-counting)

Token counting enables you to determine the number of tokens in a message before sending it to Claude, helping you make informed decisions about your prompts and usage. With token counting, you can

- Proactively manage rate limits and costs
- Make smart model routing decisions
- Optimize prompts to be a specific length

---

### How to count message tokens

The [token counting](https://docs.claude.com/en/api/messages-count-tokens) endpoint accepts the same structured list of inputs for creating a message, including support for system prompts, [tools](https://docs.claude.com/en/docs/agents-and-tools/tool-use/overview), [images](https://docs.claude.com/en/docs/build-with-claude/vision), and [PDFs](https://docs.claude.com/en/docs/build-with-claude/pdf-support). The response contains the total number of input tokens.

> [!NOTE]
>
> The token count should be considered an **estimate**. In some cases, the actual number of input tokens used when creating a message may differ by a small amount.
>
> Token counts may include tokens added automatically by Anthropic for system optimizations. **You are not billed for system-added tokens**. Billing reflects only your content.

#### Supported models

All [active models](https://docs.claude.com/en/docs/about-claude/models/overview) support token counting.

#### Count tokens in basic messages

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.count_tokens( model="claude-sonnet-4-5", system="You are a scientist", messages=[{ "role": "user", "content": "Hello, Claude" }], )

print(response.json())

```

```typescript
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic();

const response = await client.messages.countTokens({
	model: 'claude-sonnet-4-5',
	system: 'You are a scientist',
	messages: [
		{
			role: 'user',
			content: 'Hello, Claude',
		},
	],
});

console.log(response);
```

```bash
curl https://api.anthropic.com/v1/messages/count_tokens \
    --header "x-api-key: $ANTHROPIC_API_KEY" \
    --header "content-type: application/json" \
    --header "anthropic-version: 2023-06-01" \
    --data '{
      "model": "claude-sonnet-4-5",
      "system": "You are a scientist",
      "messages": [{
        "role": "user",
        "content": "Hello, Claude"
      }]
    }'
```

```java
import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.MessageCountTokensParams;
import com.anthropic.models.messages.MessageTokensCount;
import com.anthropic.models.messages.Model;

public class CountTokensExample {

  public static void main(String[] args) {
    AnthropicClient client = AnthropicOkHttpClient.fromEnv();

    MessageCountTokensParams params = MessageCountTokensParams.builder()
        .model(Model.CLAUDE_SONNET_4_20250514)
        .system("You are a scientist")
        .addUserMessage("Hello, Claude")
        .build();

    MessageTokensCount count = client.messages().countTokens(params);
    System.out.println(count);
  }
}
```

```JSON
{ "input_tokens": 14 }
```

#### Count tokens in messages with tools

> [!NOTE]
>
> > [Server tool](https://docs.claude.com/en/docs/agents-and-tools/tool-use/overview#server-tools) token counts only apply to the first sampling call.

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.count_tokens( model="claude-sonnet-4-5", tools=[ { "name": "get_weather", "description": "Get the current weather in a given location", "input_schema": { "type": "object", "properties": { "location": { "type": "string", "description": "The city and state, e.g. San Francisco, CA", } }, "required": ["location"], }, } ], messages=[{"role": "user", "content": "What's the weather like in San Francisco?"}] )

print(response.json())

```

```typescript
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic();

const response = await client.messages.countTokens({
	model: 'claude-sonnet-4-5',
	tools: [
		{
			name: 'get_weather',
			description: 'Get the current weather in a given location',
			input_schema: {
				type: 'object',
				properties: {
					location: {
						type: 'string',
						description: 'The city and state, e.g. San Francisco, CA',
					},
				},
				required: ['location'],
			},
		},
	],
	messages: [{ role: 'user', content: "What's the weather like in San Francisco?" }],
});

console.log(response);
```

```bash
curl https://api.anthropic.com/v1/messages/count_tokens \
    --header "x-api-key: $ANTHROPIC_API_KEY" \
    --header "content-type: application/json" \
    --header "anthropic-version: 2023-06-01" \
    --data '{
      "model": "claude-sonnet-4-5",
      "tools": [
        {
          "name": "get_weather",
          "description": "Get the current weather in a given location",
          "input_schema": {
            "type": "object",
            "properties": {
              "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA"
              }
            },
            "required": ["location"]
          }
        }
      ],
      "messages": [
        {
          "role": "user",
          "content": "What'\''s the weather like in San Francisco?"
        }
      ]
    }'
```

```java
import java.util.List;
import java.util.Map;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.core.JsonValue;
import com.anthropic.models.messages.MessageCountTokensParams;
import com.anthropic.models.messages.MessageTokensCount;
import com.anthropic.models.messages.Model;
import com.anthropic.models.messages.Tool;
import com.anthropic.models.messages.Tool.InputSchema;

public class CountTokensWithToolsExample {

  public static void main(String[] args) {
    AnthropicClient client = AnthropicOkHttpClient.fromEnv();

    InputSchema schema = InputSchema.builder()
        .properties(JsonValue.from(Map.of(
            "location", Map.of(
                "type", "string",
                "description", "The city and state, e.g. San Francisco, CA"))))
        .putAdditionalProperty("required", JsonValue.from(List.of("location")))
        .build();

    MessageCountTokensParams params = MessageCountTokensParams.builder()
        .model(Model.CLAUDE_SONNET_4_20250514)
        .addTool(Tool.builder()
            .name("get_weather")
            .description("Get the current weather in a given location")
            .inputSchema(schema)
            .build())
        .addUserMessage("What's the weather like in San Francisco?")
        .build();

    MessageTokensCount count = client.messages().countTokens(params);
    System.out.println(count);
  }
}
```

```JSON
{ "input_tokens": 403 }
```

#### Count tokens in messages with images

```bash
#!/bin/sh

IMAGE_URL="https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg" IMAGE_MEDIA_TYPE="image/jpeg" IMAGE_BASE64=$(curl "$IMAGE_URL" | base64)

curl https://api.anthropic.com/v1/messages/count_tokens \
--header "x-api-key: $ANTHROPIC_API_KEY" \
     --header "anthropic-version: 2023-06-01" \
     --header "content-type: application/json" \
     --data \
'{
    "model": "claude-sonnet-4-5",
    "messages": [
        {"role": "user", "content": [
            {"type": "image", "source": {
                "type": "base64",
                "media_type": "'$IMAGE_MEDIA_TYPE'", "data": "'$IMAGE_BASE64'" }}, {"type": "text", "text": "Describe this image"} ]} ] }'

```

```Python
import anthropic
import base64
import httpx

image_url = "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
image_media_type = "image/jpeg"
image_data = base64.standard_b64encode(httpx.get(image_url).content).decode("utf-8")

client = anthropic.Anthropic()

response = client.messages.count_tokens(
    model="claude-sonnet-4-5",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image_media_type,
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": "Describe this image"
                }
            ],
        }
    ],
)
print(response.json())
```

```Typescript
import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic();

const image_url = "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
const image_media_type = "image/jpeg"
const image_array_buffer = await ((await fetch(image_url)).arrayBuffer());
const image_data = Buffer.from(image_array_buffer).toString('base64');

const response = await anthropic.messages.countTokens({
  model: 'claude-sonnet-4-5',
  messages: [
    {
      "role": "user",
      "content": [
        {
          "type": "image",
          "source": {
            "type": "base64",
            "media_type": image_media_type,
            "data": image_data,
          },
        }
      ],
    },
    {
      "type": "text",
      "text": "Describe this image"
    }
  ]
});
console.log(response);
```

```java
import java.util.Base64;
import java.util.List;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.Base64ImageSource;
import com.anthropic.models.messages.ContentBlockParam;
import com.anthropic.models.messages.ImageBlockParam;
import com.anthropic.models.messages.MessageCountTokensParams;
import com.anthropic.models.messages.MessageTokensCount;
import com.anthropic.models.messages.Model;
import com.anthropic.models.messages.TextBlockParam;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class CountTokensImageExample {

  public static void main(String[] args) throws Exception {
    AnthropicClient client = AnthropicOkHttpClient.fromEnv();

    String imageUrl = "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg";
    String imageMediaType = "image/jpeg";

    HttpClient httpClient = HttpClient.newHttpClient();
    HttpRequest request = HttpRequest.newBuilder()
        .uri(URI.create(imageUrl))
        .build();
    byte[] imageBytes = httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray()).body();
    String imageBase64 = Base64.getEncoder().encodeToString(imageBytes);

    ContentBlockParam imageBlock = ContentBlockParam.ofImage(
        ImageBlockParam.builder()
            .source(Base64ImageSource.builder()
                .mediaType(Base64ImageSource.MediaType.IMAGE_JPEG)
                .data(imageBase64)
                .build())
            .build());

    ContentBlockParam textBlock = ContentBlockParam.ofText(
        TextBlockParam.builder()
            .text("Describe this image")
            .build());

    MessageCountTokensParams params = MessageCountTokensParams.builder()
        .model(Model.CLAUDE_SONNET_4_20250514)
        .addUserMessageOfBlockParams(List.of(imageBlock, textBlock))
        .build();

    MessageTokensCount count = client.messages().countTokens(params);
    System.out.println(count);
  }
}
```

```JSON
{ "input_tokens": 1551 }
```

#### Count tokens in messages with extended thinking

> [!NOTE]
>
> > [See here](https://docs.claude.com/en/docs/build-with-claude/extended-thinking#how-context-window-is-calculated-with-extended-thinking) for more details about how the context window is calculated with extended thinking
>
> - Thinking blocks from **previous** assistant turns are ignored and **do not** count toward your input tokens
> - **Current** assistant turn thinking **does** count toward your input tokens

```bash
curl https://api.anthropic.com/v1/messages/count_tokens \
    --header "x-api-key: $ANTHROPIC_API_KEY" \
    --header "content-type: application/json" \
    --header "anthropic-version: 2023-06-01" \
    --data '{
      "model": "claude-sonnet-4-5",
      "thinking": {
        "type": "enabled",
        "budget_tokens": 16000
      },
      "messages": [
        {
          "role": "user",
          "content": "Are there an infinite number of prime numbers such that n mod 4 == 3?"
        },
        {
          "role": "assistant",
          "content": [
            {
             "type": "thinking",
              "thinking": "This is a nice number theory question. Lets think about it step by step...",
              "signature": "EuYBCkQYAiJAgCs1le6/Pol5Z4/JMomVOouGrWdhYNsH3ukzUECbB6iWrSQtsQuRHJID6lWV..."
            },
            {
              "type": "text",
              "text": "Yes, there are infinitely many prime numbers p such that p mod 4 = 3..."
            }
          ]
        },
        {
          "role": "user",
          "content": "Can you write a formal proof?"
        }
      ]
    }'
```

```Python
import anthropic

client = anthropic.Anthropic()

response = client.messages.count_tokens(
    model="claude-sonnet-4-5",
    thinking={
        "type": "enabled",
        "budget_tokens": 16000
    },
    messages=[
        {
            "role": "user",
            "content": "Are there an infinite number of prime numbers such that n mod 4 == 3?"
        },
        {
            "role": "assistant",
            "content": [
                {
                    "type": "thinking",
                    "thinking": "This is a nice number theory question. Let's think about it step by step...",
                    "signature": "EuYBCkQYAiJAgCs1le6/Pol5Z4/JMomVOouGrWdhYNsH3ukzUECbB6iWrSQtsQuRHJID6lWV..."
                },
                {
                  "type": "text",
                  "text": "Yes, there are infinitely many prime numbers p such that p mod 4 = 3..."
                }
            ]
        },
        {
            "role": "user",
            "content": "Can you write a formal proof?"
        }
    ]
)

print(response.json())
```

```typescript
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic();

const response = await client.messages.countTokens({
	model: 'claude-sonnet-4-5',
	thinking: {
		type: 'enabled',
		budget_tokens: 16000,
	},
	messages: [
		{
			role: 'user',
			content: 'Are there an infinite number of prime numbers such that n mod 4 == 3?',
		},
		{
			role: 'assistant',
			content: [
				{
					type: 'thinking',
					thinking: "This is a nice number theory question. Let's think about it step by step...",
					signature: 'EuYBCkQYAiJAgCs1le6/Pol5Z4/JMomVOouGrWdhYNsH3ukzUECbB6iWrSQtsQuRHJID6lWV...',
				},
				{
					type: 'text',
					text: 'Yes, there are infinitely many prime numbers p such that p mod 4 = 3...',
				},
			],
		},
		{
			role: 'user',
			content: 'Can you write a formal proof?',
		},
	],
});

console.log(response);
```

```java
import java.util.List;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.ContentBlockParam;
import com.anthropic.models.messages.MessageCountTokensParams;
import com.anthropic.models.messages.MessageTokensCount;
import com.anthropic.models.messages.Model;
import com.anthropic.models.messages.TextBlockParam;
import com.anthropic.models.messages.ThinkingBlockParam;

public class CountTokensThinkingExample {

  public static void main(String[] args) {
    AnthropicClient client = AnthropicOkHttpClient.fromEnv();

    List<ContentBlockParam> assistantBlocks = List.of(
        ContentBlockParam.ofThinking(ThinkingBlockParam.builder()
            .thinking("This is a nice number theory question. Let's think about it step by step...")
            .signature("EuYBCkQYAiJAgCs1le6/Pol5Z4/JMomVOouGrWdhYNsH3ukzUECbB6iWrSQtsQuRHJID6lWV...")
            .build()),
        ContentBlockParam.ofText(TextBlockParam.builder()
            .text("Yes, there are infinitely many prime numbers p such that p mod 4 = 3...")
            .build()));

    MessageCountTokensParams params = MessageCountTokensParams.builder()
        .model(Model.CLAUDE_SONNET_4_20250514)
        .enabledThinking(16000)
        .addUserMessage("Are there an infinite number of prime numbers such that n mod 4 == 3?")
        .addAssistantMessageOfBlockParams(assistantBlocks)
        .addUserMessage("Can you write a formal proof?")
        .build();

    MessageTokensCount count = client.messages().countTokens(params);
    System.out.println(count);
  }
}
```

```JSON
{ "input_tokens": 88 }
```

#### Count tokens in messages with PDFs

> [!NOTE]
>
> Token counting supports PDFs with the same [limitations](https://docs.claude.com/en/docs/build-with-claude/pdf-support#pdf-support-limitations) as the Messages API.

```bash
curl https://api.anthropic.com/v1/messages/count_tokens \
    --header "x-api-key: $ANTHROPIC_API_KEY" \
    --header "content-type: application/json" \
    --header "anthropic-version: 2023-06-01" \
    --data '{
      "model": "claude-sonnet-4-5",
      "messages": [{
        "role": "user",
        "content": [
          {
            "type": "document",
            "source": {
              "type": "base64",
              "media_type": "application/pdf",
              "data": "'$(base64 -i document.pdf)'"
            }
          },
          {
            "type": "text",
            "text": "Please summarize this document."
          }
        ]
      }]
    }'
```

```Python
import base64
import anthropic

client = anthropic.Anthropic()

with open("document.pdf", "rb") as pdf_file:
    pdf_base64 = base64.standard_b64encode(pdf_file.read()).decode("utf-8")

response = client.messages.count_tokens(
    model="claude-sonnet-4-5",
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_base64
                }
            },
            {
                "type": "text",
                "text": "Please summarize this document."
            }
        ]
    }]
)

print(response.json())
```

```Typescript
import Anthropic from '@anthropic-ai/sdk';
import { readFileSync } from 'fs';

const client = new Anthropic();

const pdfBase64 = readFileSync('document.pdf', { encoding: 'base64' });

const response = await client.messages.countTokens({
  model: 'claude-sonnet-4-5',
  messages: [{
    role: 'user',
    content: [
      {
        type: 'document',
        source: {
          type: 'base64',
          media_type: 'application/pdf',
          data: pdfBase64
        }
      },
      {
        type: 'text',
        text: 'Please summarize this document.'
      }
    ]
  }]
});

console.log(response);
```

```java
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
import java.util.List;

import com.anthropic.client.AnthropicClient;
import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.Base64PdfSource;
import com.anthropic.models.messages.ContentBlockParam;
import com.anthropic.models.messages.DocumentBlockParam;
import com.anthropic.models.messages.MessageCountTokensParams;
import com.anthropic.models.messages.MessageTokensCount;
import com.anthropic.models.messages.Model;
import com.anthropic.models.messages.TextBlockParam;

public class CountTokensPdfExample {

  public static void main(String[] args) throws Exception {
    AnthropicClient client = AnthropicOkHttpClient.fromEnv();

    byte[] fileBytes = Files.readAllBytes(Path.of("document.pdf"));
    String pdfBase64 = Base64.getEncoder().encodeToString(fileBytes);

    ContentBlockParam documentBlock = ContentBlockParam.ofDocument(
        DocumentBlockParam.builder()
            .source(Base64PdfSource.builder()
                .mediaType(Base64PdfSource.MediaType.APPLICATION_PDF)
                .data(pdfBase64)
                .build())
            .build());

    ContentBlockParam textBlock = ContentBlockParam.ofText(
        TextBlockParam.builder()
            .text("Please summarize this document.")
            .build());

    MessageCountTokensParams params = MessageCountTokensParams.builder()
        .model(Model.CLAUDE_SONNET_4_20250514)
        .addUserMessageOfBlockParams(List.of(documentBlock, textBlock))
        .build();

    MessageTokensCount count = client.messages().countTokens(params);
    System.out.println(count);
  }
}
```

```JSON
{ "input_tokens": 2188 }
```

---

### Pricing and rate limits

Token counting is **free to use** but subject to requests per minute rate limits based on your [usage tier](https://docs.claude.com/en/api/rate-limits#rate-limits). If you need higher limits, contact sales through the [Claude Console](https://console.anthropic.com/settings/limits).

| Usage tier | Requests per minute (RPM) |
| ---------- | ------------------------- |
| 1          | 100                       |
| 2          | 2,000                     |
| 3          | 4,000                     |
| 4          | 8,000                     |

> [!NOTE]
>
> Token counting and message creation have separate and independent rate limits -- usage of one does not count against the limits of the other.

---

### FAQ

No, token counting provides an estimate without using caching logic. While you may provide `cache_control` blocks in your token counting request, prompt caching only occurs during actual message creation.

---

## [Use prompt templates and variables](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/prompt-templates-and-variables)

When deploying an LLM-based application with Claude, your API calls will typically consist of two types of content:

- **Fixed content:** Static instructions or context that remain constant across multiple interactions
- **Variable content:** Dynamic elements that change with each request or conversation, such as:
  - User inputs
  - Retrieved content for Retrieval-Augmented Generation (RAG)
  - Conversation context such as user account history
  - System-generated data such as tool use results fed in from other independent calls to Claude

A **prompt template** combines these fixed and variable parts, using placeholders for the dynamic content. In the [Claude Console](https://console.anthropic.com/), these placeholders are denoted with **\{\{double brackets}}**, making them easily identifiable and allowing for quick testing of different values.

---

### When to use prompt templates and variables

You should always use prompt templates and variables when you expect any part of your prompt to be repeated in another call to Claude (only via the API or the [Claude Console](https://console.anthropic.com/). [claude.ai](https://claude.ai/) currently does not support prompt templates or variables).

Prompt templates offer several benefits:

- **Consistency:** Ensure a consistent structure for your prompts across multiple interactions
- **Efficiency:** Easily swap out variable content without rewriting the entire prompt
- **Testability:** Quickly test different inputs and edge cases by changing only the variable portion
- **Scalability:** Simplify prompt management as your application grows in complexity
- **Version control:** Easily track changes to your prompt structure over time by keeping tabs only on the core part of your prompt, separate from dynamic inputs

The [Claude Console](https://console.anthropic.com/) heavily uses prompt templates and variables in order to support features and tooling for all the above, such as with the:

- **[Prompt generator](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/prompt-generator):** Decides what variables your prompt needs and includes them in the template it outputs
- **[Prompt improver](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/prompt-improver):** Takes your existing template, including all variables, and maintains them in the improved template it outputs
- **[Evaluation tool](https://docs.claude.com/en/docs/test-and-evaluate/eval-tool):** Allows you to easily test, scale, and track versions of your prompts by separating the variable and fixed portions of your prompt template

---

### Example prompt template

Let's consider a simple application that translates English text to Spanish. The translated text would be variable since you would expect this text to change between users or calls to Claude. This translated text could be dynamically retrieved from databases or the user's input.

Thus, for your translation app, you might use this simple prompt template:

```text
Translate this text from English to Spanish: {{text}}
```

---

### Next steps

<CardGroup cols={2}>
  <Card title="Generate a prompt" icon="link" href="/en/docs/build-with-claude/prompt-engineering/prompt-generator">
    Learn about the prompt generator in the Claude Console and try your hand at getting Claude to generate a prompt for you.
  </Card>

  <Card title="Apply XML tags" icon="link" href="/en/docs/build-with-claude/prompt-engineering/use-xml-tags">
    If you want to level up your prompt variable game, wrap them in XML tags.
  </Card>

  <Card title="Claude Console" icon="link" href="https://console.anthropic.com/">
    Check out the myriad prompt development tools available in the Claude Console.
  </Card>
</CardGroup>

---

## [Use XML tags to structure your prompts](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags)

> [!NOTE]
>
> While these tips apply broadly to all Claude models, you can find prompting tips specific to [extended thinking models here](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/extended-thinking-tips).

When your prompts involve multiple components like context, instructions, and examples, XML tags can be a game-changer. They help Claude parse your prompts more accurately, leading to higher-quality outputs.

> [!TIP]
>
> **XML tip**: Use tags like `<instructions>`, `<example>`, and `<formatting>` to clearly separate different parts of your prompt. This prevents Claude from mixing up instructions with examples or context.

### Why use XML tags?

- **Clarity:** Clearly separate different parts of your prompt and ensure your prompt is well structured.
- **Accuracy:** Reduce errors caused by Claude misinterpreting parts of your prompt.
- **Flexibility:** Easily find, add, remove, or modify parts of your prompt without rewriting everything.
- **Parseability:** Having Claude use XML tags in its output makes it easier to extract specific parts of its response by post-processing.

> [!NOTE]
>
> There are no canonical "best" XML tags that Claude has been trained with in particular, although we recommend that your tag names make sense with the information they surround.

---

### Tagging best practices

1. **Be consistent**: Use the same tag names throughout your prompts, and refer to those tag names when talking about the content (e.g, `Using the contract in <contract> tags...`).
2. **Nest tags**: You should nest tags `<outer><inner></inner></outer>` for hierarchical content.

> [!TIP]
>
> **Power user tip**: Combine XML tags with other techniques like multishot prompting (`<examples>`) or chain of thought (`<thinking>`, `<answer>`). This creates super-structured, high-performance prompts.

#### Examples

Without XML tags, Claude misunderstands the task and generates a report that doesn't match the required structure or tone. After substitution, there is also a chance that Claude misunderstands where one section (like the the Q1 report example) stops and another begins.

| Role      | No XML Tags                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | With XML Tags                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Assistant | Q2 Financial Report for AcmeCorp Investors<br /><br />Dear Valued Investors,<br /><br />I am pleased to present our Q2 financial report, showcasing AcmeCorp's continued growth and resilience in the B2B SaaS market.<br /><br />1. Revenue Growth:<br />Our Q2 revenue reached \$15.2M, a 22% YoY increase. This growth is primarily driven by a 30% expansion in our enterprise client base. However, our SMB segment saw a slight decline of 5%, which we aim to address through targeted marketing initiatives in Q3.<br /><br />2. Profit Margins:<br />Gross margin improved to 72% (up 3% from Q1) due to infrastructure optimizations. EBITDA margin, however, dipped to 18% (down 2%) as we invested heavily in R\&D for our upcoming AI-driven features.<br /><br />3. Cash Flow:<br />Operating cash flow remains strong at \$4.1M. Our cash reserves stand at \$28M, providing a 15-month runway at current burn rate. We did see a 20% increase in customer acquisition costs, which we're addressing through more efficient sales strategies.<br /><br />In summary, AcmeCorp's core financials remain robust. We're balancing growth investments with prudent cash management. Our focus for Q3 will be revitalizing SMB growth and optimizing sales efficiency.<br /><br />Thank you for your continued trust.<br /><br />Sincerely,<br />CFO, AcmeCorp | Q2 Financial Report for AcmeCorp Investors\</output><br /><br />Revenue Growth:<br />- Q2 revenue: \$15.2M (22% YoY ↑)<br />- Enterprise clients: 30% ↑<br />- SMB segment: 5% ↓<br /> Action: Targeted Q3 marketing<br /><br />Profit Margins:<br />- Gross margin: 72% (3% ↑ from Q1)<br /> Reason: Infrastructure optimizations<br />- EBITDA margin: 18% (2% ↓)<br /> Reason: R\&D investment in AI features<br /><br />Cash Flow:<br />- Operating cash flow: \$4.1M (strong)<br />- Cash reserves: \$28M (15-month runway)<br />- Customer acquisition cost: 20% ↑<br /> Action: Optimize sales strategies<br /><br />Outlook:<br />- Core financials: Robust<br />- Q3 focus: Revitalize SMB, optimize sales<br /><br />Management remains committed to balancing growth investments with financial discipline. |
| User      | You're a financial analyst at AcmeCorp. Generate a Q2 financial report for our investors. Include sections on Revenue Growth, Profit Margins, and Cash Flow, like with this example from last year: \{\{Q1_REPORT}}. Use data points from this spreadsheet: \{\{SPREADSHEET_DATA}}. The report should be extremely concise, to the point, professional, and in list format. It should and highlight both strengths and areas for improvement.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | You're a financial analyst at AcmeCorp. Generate a Q2 financial report for our investors.<br /><br />AcmeCorp is a B2B SaaS company. Our investors value transparency and actionable insights.<br /><br />Use this data for your report:\<data>\{\{SPREADSHEET_DATA}}\</data><br /><br />\<instructions><br />1. Include sections: Revenue Growth, Profit Margins, Cash Flow.<br />2. Highlight strengths and areas for improvement.<br />\</instructions><br /><br />Make your tone concise and professional. Follow this structure:<br />\<formatting_example>\{\{Q1_REPORT}}\</formatting_example>                                                                                                                                                                                                                  |

Without XML tags, Claude's analysis is disorganized and misses key points. With tags, it provides a structured, thorough analysis that a legal team can act on.

| Role      | No XML Tags                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | With XML Tags                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| User      | Analyze this software licensing agreement for potential risks and liabilities: \{\{CONTRACT}}. Focus on indemnification, limitation of liability, and IP ownership clauses. Also, note any unusual or concerning terms. Here's our standard contract for reference: \{\{STANDARD_CONTRACT}}. Give a summary of findings and recommendations for our legal team.                                                                                                                                                                                                                                                                                                                     | Analyze this software licensing agreement for legal risks and liabilities.<br /><br />We're a multinational enterprise considering this agreement for our core data infrastructure.<br /><br />\<agreement><br />\{\{CONTRACT}}\</agreement><br /><br />This is our standard contract for reference:<br />\<standard_contract>\{\{STANDARD_CONTRACT}}\</standard_contract><br /><br />\<instructions><br />1. Analyze these clauses:<br /> - Indemnification<br /> - Limitation of liability<br /> - IP ownership<br /><br />2. Note unusual or concerning terms.<br /><br />3. Compare to our standard contract.<br /><br />4. Summarize findings in \<findings> tags.<br /><br />5. List actionable recommendations in \<recommendations> tags.\</instructions>                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Assistant | The provided software licensing agreement presents several concerning aspects. The indemnification clause is overly broad, potentially exposing us to significant liabilities. The limitation of liability section caps damages at a mere \$500, which is inadequate for our enterprise-level usage. Regarding IP, the agreement grants the vendor joint ownership of any modifications or integrations we create.<br /><br />In summary, this agreement is not in our best interest. It exposes us to undue risk, limits our recourse in case of failures, and compromises our intellectual property rights. I recommend renegotiating these terms or seeking alternative vendors. | \<findings><br />1. Indemnification (Clause 8):<br /> - Issue: Overly broad. We indemnify vendor against "any and all claims" arising from our use.<br /> - Risk: Could hold us liable even for vendor's negligence or product defects.<br /> - Deviation: Our standard limits indemnity to claims arising from our violation of agreement.<br /><br />2. Limitation of Liability (Clause 9):<br /> - Issue: Caps all damages at \$500, including direct damages.<br /> - Risk: Grossly inadequate for enterprise use. A critical failure could cost millions.<br /> - Deviation: Our standard allows for direct damages up to 12 months of fees paid.<br /><br />3. IP Ownership (Clause 12):<br /> - Issue: Grants vendor joint ownership of our modifications/integrations.<br /> - Risk: Vendor could use or sell our proprietary algorithms or data insights.<br /> - Deviation: Our standard retains full ownership of our work.<br /><br />4. Unusual Terms:<br /> - Clause 5.3: Vendor can use our usage data for "any purpose."<br /> - Clause 7.2: Vendor can terminate for "convenience" with only 7 days' notice.<br /> - Clause 11: No warranties of any kind, even for basic merchantability.<br />\</findings><br /><br />\<recommendations><br />1. Reject this agreement. Risks far outweigh benefits for an enterprise.<br />2. Counter-propose:<br /> - Indemnification: Limit to claims arising from our violation of agreement.<br /> - Liability: Cap at 12 months' fees for direct damages; negotiate for indirect.<br /> - IP: Full ownership of our modifications/integrations.<br /> - Data Use: Restrict to service improvement only.<br /> - Termination: Minimum 90 days' notice; only for cause.<br /> - Warranties: Demand basic merchantability and fitness for purpose.<br />3. If vendor refuses, explore alternative providers or in-house solutions.<br />4. Engage legal counsel for contract negotiation given high stakes.<br />\</recommendations> |

---

<CardGroup cols={3}>
  <Card title="Prompt library" icon="link" href="/en/resources/prompt-library/library">
    Get inspired by a curated selection of prompts for various tasks and use cases.
  </Card>

  <Card title="GitHub prompting tutorial" icon="link" href="https://github.com/anthropics/prompt-eng-interactive-tutorial">
    An example-filled tutorial that covers the prompt engineering concepts found in our docs.
  </Card>

  <Card title="Google Sheets prompting tutorial" icon="link" href="https://docs.google.com/spreadsheets/d/19jzLgRruG9kjUQNKtCg1ZjdD6l6weA6qRXG5zLIAhC8">
    A lighter weight version of our prompt engineering tutorial via an interactive spreadsheet.
  </Card>
</CardGroup>

---

## [Giving Claude a role with a system prompt](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/system-prompts)

> [!NOTE]
>
> While these tips apply broadly to all Claude models, you can find prompting tips specific to [extended thinking models here](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/extended-thinking-tips).

When using Claude, you can dramatically improve its performance by using the `system` parameter to give it a role. This technique, known as role prompting, is the most powerful way to use system prompts with Claude.

The right role can turn Claude from a general assistant into your virtual domain expert!

> [!TIP]
>
> **System prompt tips**: Use the `system` parameter to set Claude's role. Put everything else, like task-specific instructions, in the `user` turn instead.

### Why use role prompting?

- **Enhanced accuracy:** In complex scenarios like legal analysis or financial modeling, role prompting can significantly boost Claude's performance.
- **Tailored tone:** Whether you need a CFO's brevity or a copywriter's flair, role prompting adjusts Claude's communication style.
- **Improved focus:** By setting the role context, Claude stays more within the bounds of your task's specific requirements.

---

### How to give Claude a role

Use the `system` parameter in the [Messages API](https://docs.claude.com/en/api/messages) to set Claude's role:

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=2048,
    system="You are a seasoned data scientist at a Fortune 500 company.", # <-- role prompt
    messages=[
        {"role": "user", "content": "Analyze this dataset for anomalies: <dataset>{{DATASET}}</dataset>"}
    ]
)

print(response.content)
```

> [!TIP]
>
> **Role prompting tip**: Experiment with roles! A `data scientist` might see different insights than a `marketing strategist` for the same data. A `data scientist specializing in customer insight analysis for Fortune 500 companies` might yield different results still!

---

### Examples

#### Example 1: Legal contract analysis

Without a role, Claude might miss critical issues:

| Role      | Content                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| User      | Analyze this software licensing agreement for potential risks:<br />\<contract><br />\{\{CONTRACT}}<br />\</contract><br /><br />Focus on indemnification, liability, and IP ownership.                                                                                                                                                                                                                                                                                                                        |
| Assistant | Here's a summary of the key points in the software licensing agreement:<br /><br />1. Indemnification (Section 8):<br /> - We indemnify the vendor against claims arising from our use.<br /><br />2. Limitation of Liability (Section 9):<br /> - Damages capped at \$500.<br /><br />3. IP Ownership (Section 12):<br /> - We retain ownership of our modifications.<br /><br />Overall, the agreement seems standard. The indemnification and liability clauses are typical, and we maintain our IP rights. |

With a role, Claude catches critical issues that could cost millions:

| Role      | Content                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| User      | You are the General Counsel of a Fortune 500 tech company. We're considering this software licensing agreement for our core data infrastructure:<br />\<contract><br />\{\{CONTRACT}}<br />\</contract><br /><br />Analyze it for potential risks, focusing on indemnification, liability, and IP ownership. Give your professional opinion.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| Assistant | I've reviewed the software licensing agreement, and I have serious concerns that could expose our company to significant risks:<br /><br />1. Indemnification (Section 8):<br /> - Critical Issue: We indemnify the vendor against "any and all claims" arising from our use.<br /> - Risk: This could hold us liable even for the vendor's negligence or product defects.<br /> - Recommendation: Reject. Limit our indemnity to claims arising from our violation of the agreement.<br /><br />2. Limitation of Liability (Section 9):<br /> - Critical Issue: Damages capped at \$500, including direct damages.<br /> - Risk: Grossly inadequate. A critical failure in our data infrastructure could cost us millions in lost revenue and reputational damage.<br /> - Recommendation: Reject. Negotiate for cap at 12 months of fees for direct damages, and carve-outs for data breaches.<br /><br />3. IP Ownership (Section 12):<br /> - Critical Issue: Vendor gains joint ownership of our modifications and integrations.<br /> - Risk: They could use or sell our proprietary algorithms or data insights to competitors.<br /> - Recommendation: Reject. We must retain full ownership of our work.<br /><br />Professional Opinion: Do not sign this agreement. It is grossly unfavorable and exposes us to unacceptable levels of risk. If the vendor refuses to renegotiate these terms, I strongly advise exploring alternative providers or accelerating our in-house solution. The potential costs of proceeding with this agreement far outweigh any short-term gains. |

#### Example 2: Financial analysis

Without a role, Claude's analysis lacks depth:

| Role      | Content                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| User      | Analyze this dataset of our Q2 financials:<br />\<data><br />\{\{FINANCIALS}}<br />\</data><br /><br />Highlight key trends and recommend actions.                                                                                                                                                                                                                                                                                                                               |
| Assistant | Here's a summary of your Q2 financials:<br /><br />1. Revenue: \$15.2M, up 22% YoY. Enterprise client base grew 30%.<br />2. Gross Margin: 72%, up 3% from Q1.<br />3. EBITDA Margin: 18%, down 2% due to R\&D investments.<br />4. Cash Flow: \$4.1M operating, \$28M in reserves.<br /><br />Overall, financials look strong with revenue growth and healthy margins. Increased R\&D spending is impacting profitability but could pay off long-term. Maintain current course. |

With a role, Claude delivers actionable insights:

| Role      | Content                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| User      | You are the CFO of a high-growth B2B SaaS company. We're in a board meeting discussing our Q2 financials:<br />\<data><br />\{\{FINANCIALS}}<br />\</data><br /><br />Analyze key trends, flag concerns, and recommend strategic actions. Our investors want aggressive growth but are wary of our burn rate.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Assistant | Board members, here's my analysis of our Q2 financials:<br /><br />1. Revenue (\$15.2M, +22% YoY):<br /> - Insight: Enterprise growth (+30%) is outpacing overall growth.<br /> - Flag: SMB segment declined 5%.<br /> - Action: Reallocate 20% of SMB marketing budget to enterprise sales. Task product to simplify SMB onboarding.<br /><br />2. Margins (Gross: 72%, +3% QoQ; EBITDA: 18%, -2% QoQ):<br /> - Insight: Infrastructure optimizations boosted gross margins.<br /> - Flag: R\&D spend on AI features dented EBITDA.<br /> - Action: No change. Our AI roadmap is critical for enterprise stickiness.<br /><br />3. Cash (\$4.1M OCF, \$28M reserves):<br /> - Insight: 15-month runway at current burn.<br /> - Flag: CAC up 20%, eroding LTV/CAC.<br /> - Action: Freeze non-essential hires. Implement sales funnel analytics to cut CAC by 15% in Q3.<br /><br />Strategic Stance: We're threading the needle between growth and burn. Enterprise focus is our growth engine—invest there. But watch SMB churn; it could bleed into enterprise. Our AI bet is sound, but we must convert it to ARR by Q4, or we cut R\&D by 30%.<br /><br />In sum: Double down on enterprise, streamline SMB, optimize sales, and monetize AI. Questions? |

---

<CardGroup cols={3}>
  <Card title="Prompt library" icon="link" href="/en/resources/prompt-library/library">
    Get inspired by a curated selection of prompts for various tasks and use cases.
  </Card>

  <Card title="GitHub prompting tutorial" icon="link" href="https://github.com/anthropics/prompt-eng-interactive-tutorial">
    An example-filled tutorial that covers the prompt engineering concepts found in our docs.
  </Card>

  <Card title="Google Sheets prompting tutorial" icon="link" href="https://docs.google.com/spreadsheets/d/19jzLgRruG9kjUQNKtCg1ZjdD6l6weA6qRXG5zLIAhC8">
    A lighter weight version of our prompt engineering tutorial via an interactive spreadsheet.
  </Card>
</CardGroup>
