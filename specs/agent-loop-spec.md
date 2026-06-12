# Spec: `run_agent()`

**File:** `agent.py`
**Status:** Partially pre-filled — complete the two blank fields before implementing

---

## Purpose

Orchestrate a single conversational turn for the Plant Advisor agent. Given a user message and the conversation history, call the LLM with available tools, execute any tool calls the LLM requests, and return the final text response.

This is the core of what makes Plant Advisor an _agent_ rather than a simple chatbot: the ability to decide which tools to call, use their results to inform its response, and loop until it has everything it needs.

---

## Input / Output Contract

**Inputs:**

| Parameter      | Type   | Description                                                             |
| -------------- | ------ | ----------------------------------------------------------------------- |
| `user_message` | `str`  | The user's current message                                              |
| `history`      | `list` | Gradio conversation history — list of `[user_msg, assistant_msg]` pairs |

**Output:** `str`

The agent's final text response for this turn. Should never be empty — if something goes wrong, return a user-readable fallback message.

---

## Design Decisions

_Read `specs/system-design.md` (especially the "How the Groq Tool Calling API Works" section) before reviewing these. Complete the two blank fields before writing any code._

---

### Messages list structure

The messages list must start with the system prompt, then replay the conversation
history, then add the new user message. Gradio history is a list of `[user, assistant]`
pairs — convert each pair to two API-format dicts:

```python
messages = [{"role": "system", "content": SYSTEM_PROMPT}]

for user_msg, assistant_msg in history:
    messages.append({"role": "user", "content": user_msg})
    if assistant_msg:
        messages.append({"role": "assistant", "content": assistant_msg})

messages.append({"role": "user", "content": user_message})
```

---

### Initial LLM call

Pass the model, the messages list, the tool definitions, and `tool_choice="auto"`
so the LLM can decide whether to call a tool or respond directly:

```python
response = client.chat.completions.create(
    model=LLM_MODEL,
    messages=messages,
    tools=TOOL_DEFINITIONS,
    tool_choice="auto",
)
```

---

### Detecting tool calls in the response

The response object has a `choices` list. Index 0 gives the assistant message.
Check its `tool_calls` attribute — if it's truthy, the LLM wants to call tools:

```python
assistant_message = response.choices[0].message

if not assistant_message.tool_calls:
    # No tool calls — LLM has a final answer
    ...
```

---

### Appending the assistant message

When there are tool calls, append the full assistant message object to `messages`
**before** appending any tool results. The API requires this ordering — a tool
result message must immediately follow the assistant message that requested it:

```python
messages.append(assistant_message)  # must come first
```

---

### Executing and appending tool results

For each tool call, extract the name and arguments, call `dispatch_tool()`, and
append the result as a `"tool"` role message. The `tool_call_id` links this result
back to the specific tool call that requested it:

```python
for tool_call in assistant_message.tool_calls:
    tool_name = tool_call.function.name
    tool_args = json.loads(tool_call.function.arguments)
    tool_result = dispatch_tool(tool_name, tool_args)

    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,
        "content": tool_result,
    })
```

---

### Loop termination conditions

_The loop should stop when: (a) the LLM returns a response with no tool calls, OR (b) the MAX_TOOL_ROUNDS limit is reached. Describe how you will detect each condition and what you will return in each case._

```
(a) If the LLM returns a response with no tool calls, return the assistant's text message.
(b) If MAX_TOOL_ROUNDS limit is reached, return "I was unable to complete the request. Please try again."
```

---

### Extracting the final text response

_Once the loop exits because there are no more tool calls, how do you extract the text content from the response object? What field holds the string you should return?_

```
Once the loop exits because there are no more tool calls, the final text is extracted from: assistant_message.content
where `assistant_message = response.choices[0].message`.
The full path from the raw response object is: response.choices[0].message.content
```

---

## Implementation Notes

_Fill this in after implementing and testing._

**Trace of a working agent turn (what tools were called and in what order):**

```
Query: "How should I care for my calathea?"
Round 1 Tool call: lookup_plant({'plant_name': 'calathea'})
Round 2 tool call: [tool name, args] (if any)
Final response: Based on the database information, to care for your Calathea, you should keep the soil consistently moist but not soggy, and use filtered, distilled, or rainwater to prevent brown edges. Let the water sit overnight if using tap water. The plant prefers low to medium indirect light, and direct sun will bleach and damage the leaf markings. It requires high humidity (50%+), so you can use a humidifier, mist frequently, or group it with other plants. The ideal temperature is between 60-80°F (15-27°C), and it's sensitive to cold drafts and temperatures below 55°F. Fertilize monthly during the growing season with a diluted balanced fertilizer. Some common issues to watch out for include brown leaf edges, leaf curling, and yellowing, which can be caused by tap water minerals, dry air, underwatering, or overwatering.

Please note that Calatheas can be finicky, so it's normal for them to require some adjustment time in a new home. If you have any further questions or concerns, feel free to ask!
```

**What happens when you ask about a plant that isn't in the database?**

```
The agent first calls lookup_plant() with the common name ("string of pearls"),
which returns found: False. It then automatically tries the scientific name
("Senecio rowleyanus") without being instructed to — also not found.

After updating the not-found message and system prompt, the agent identified
"string of pearls" as a succulent and made a third tool call: lookup_plant("succulent"),
which succeeded. The final response used real database data while clearly
telling the user it was general succulent guidance, not string-of-pearls-specific data.
```

**One thing about the tool call API that surprised you:**

```
The LLM made decisions we never explicitly coded. For example, it autonomously
tried the scientific name as a second lookup attempt, and after the prompt update,
it independently decided to look up "succulent" as a fallback. The tool call API
doesn't just execute instructions — the LLM actively reasons about which tools
to call and in what order based on context.
```
