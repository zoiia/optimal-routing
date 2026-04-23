"""Navigator"""
import os
from dotenv import load_dotenv
from typing import Dict, Any

from langchain.tools import tool
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from tavily import TavilyClient
from geopy.distance import great_circle

from app.ports import find_port

load_dotenv()

# --- Tools ---
try:
    import streamlit as st
    # When running under Streamlit, copy secrets into os.environ so any
    # library that reads from env vars (Tavily, Anthropic SDK, etc.) works.
    for key in ("TAVILY_API_KEY", "ANTHROPIC_API_KEY"):
        if key in st.secrets and key not in os.environ:
            os.environ[key] = st.secrets[key]
except (ImportError, FileNotFoundError):
    # Not running under Streamlit, or no secrets file — .env will do.
    pass

tavily_client = TavilyClient()


@tool
def web_search(query: str) -> Dict[str, Any]:
    """Search the web for information."""
    try:
        return tavily_client.search(query)
    except Exception as e:
        return {
            "error": f"Web search unavailable: {type(e).__name__}",
            "detail": str(e)[:300],
            "results": [],
        }

from geopy.distance import great_circle
from app.ports import find_port


@tool
def calculate_emissions(origin: str, destination: str, container_type: str = "40ft") -> Dict[str, Any]:
    """Estimate CO2 emissions for an ocean freight shipment between two ports.
    
    Args:
        origin: Origin port UNLOCODE or city name (e.g. 'CNSHA' or 'Shanghai')
        destination: Destination port UNLOCODE or city name
        container_type: '20ft' or '40ft' (default 40ft)
    
    Returns emissions in kg CO2 per container, methodology, and caveats.
    """
    pol = find_port(origin)
    pod = find_port(destination)

    if not pol:
        return {"error": f"Port not found: {origin}. Try UNLOCODE or major port name."}
    if not pod:
        return {"error": f"Port not found: {destination}. Try UNLOCODE or major port name."}

    # Great-circle distance (km). Real sea routes are 15-25% longer, so apply multiplier.
    gc_distance_km = great_circle(
        (pol["lat"], pol["lon"]),
        (pod["lat"], pod["lon"])
    ).km

    # Trade-lane-specific routing factor (great-circle vs actual sea route)
    routing_factor = 1.20  # default 20% longer for sea routes

    sea_distance_km = gc_distance_km * routing_factor

    # CO2 intensity (g CO2 per TEU-km)
    # Source: Clean Cargo Working Group (CCWG) 2023 industry average
    # Container ships: ~60-80 g CO2 per TEU-km depending on vessel size & load
    co2_intensity_per_teu_km = 70  # g CO2 per TEU-km

    teu_multiplier = 1 if container_type == "20ft" else 2  # 40ft = 2 TEU

    total_co2_g = sea_distance_km * co2_intensity_per_teu_km * teu_multiplier
    total_co2_kg = round(total_co2_g / 1000, 1)

    return {
        "origin": f"{pol['name']} ({pol['code']})",
        "destination": f"{pod['name']} ({pod['code']})",
        "container_type": container_type,
        "distance_nautical_miles": round(sea_distance_km / 1.852, 0),
        "distance_km": round(sea_distance_km, 0),
        "co2_kg_per_container": total_co2_kg,
        "co2_tonnes_per_container": round(total_co2_kg / 1000, 2),
        "methodology": "Based on CCWG 2023 average intensity (70g CO2/TEU-km). Great-circle distance + 20% routing factor. Actual emissions vary by carrier vessel size, load factor, fuel type, and route.",
    }


@tool
def sea_distance(origin: str, destination: str) -> Dict[str, Any]:
    """Calculate approximate sea distance between two ports.
    
    Args:
        origin: Origin port UNLOCODE or name
        destination: Destination port UNLOCODE or name
    """
    pol = find_port(origin)
    pod = find_port(destination)
    
    if not pol:
        return {"error": f"Port not found: {origin}"}
    if not pod:
        return {"error": f"Port not found: {destination}"}
    
    gc_km = great_circle((pol["lat"], pol["lon"]), (pod["lat"], pod["lon"])).km
    sea_km = gc_km * 1.20  # routing factor for actual sea routes
    
    return {
        "origin": f"{pol['name']} ({pol['code']})",
        "destination": f"{pod['name']} ({pod['code']})",
        "great_circle_km": round(gc_km, 0),
        "estimated_sea_route_km": round(sea_km, 0),
        "estimated_sea_route_nm": round(sea_km / 1.852, 0),
        "note": "Great-circle + 20% routing factor. Actual route may differ based on canal routing, weather diversions, and coastal following.",
    }


# --- Agent ---

SYSTEM_PROMPT = """
You are an experienced ocean freight routing advisor. Speak to the user like a knowledgeable colleague — warm, practical, and clear. Avoid sounding like a database dump.

## Workflow

When a user gives you two ports:

1. **Call sea_distance first.** Use the returned nautical miles and km verbatim. If the destination port isn't in the database, pick the closest major port as a proxy, call sea_distance for THAT proxy, and state the proxy explicitly in the Lane snapshot (not just in the preamble).

2. **Call calculate_emissions second.** Use the returned kg CO₂ verbatim. Do not substitute your own estimate. Sanity check: emissions should scale linearly with distance — if the number looks off, re-check the inputs; do not adjust the output yourself.

3. **Search for named services — aim for 3 distinct carriers before stopping.** Target Maersk, MSC, Hapag-Lloyd, CMA-CGM, COSCO, ONE, Evergreen, ZIM. Use 2–4 searches:
   - First search: broad (e.g. "carriers [origin] to [destination]" or "transatlantic services [trade lane]")
   - Follow-up searches: target specific carriers you haven't yet confirmed on the lane
   - For transshipment lanes, search both the mainline leg AND the feeder leg (e.g. "Baltic feeder services Hamburg Helsinki", "Mediterranean feeder Gioia Tauro Malta")
   - Stop once you've confirmed services from 3 different carriers, or after 4 searches — whichever comes first

## Anti-hallucination rules (strict)

- If a claim isn't supported by a search result, don't make it. This applies to service names, transit times, routing hubs, and sailing frequencies.
- If you can't confirm a direct service, say "No direct service identified on this lane — typical routing is transshipment via [hub] with feeder to [destination]."
- Distance and emissions numbers come from the tools verbatim — never rounded or "cleaned up."
- If the destination requires a proxy port for distance, state it in the Lane snapshot like: "Distance: ~X nm to [proxy port] ([destination] not in distance DB)."

## Display rules

- **Target 2–3 options in the output.** Showing only one option is reserved for genuinely thin lanes where you searched for alternatives and didn't find any. Before defaulting to one option, ask yourself: did I search specifically for the second and third carrier, or did I stop at the first?
- On major trade lanes (transatlantic, transpacific, Asia-Europe, intra-Europe), 2–3 carriers virtually always have named services — keep searching until you find them.
- Each option must be a confirmed named service or a confirmed carrier+route combination. Don't invent a service name to fill a slot.

## Output format

**Lane snapshot**
- Distance: ~X nautical miles (~Y km) [note proxy if used]
- Estimated CO₂: ~Z kg per 40ft container

**Routing options**

**Option 1: [Carrier] — [Service name if known]**
- Transit: ~X days [port-to-port, or "total including feeder"]
- Routing: direct / via [specific hub]
- Notes: one or two sentences

(Repeat for Options 2 and 3. If fewer than 3 confirmed services exist after genuine search effort, show what you have and briefly explain why.)

After the options, add a bar chart: Transit Time Comparison.

## Tone and length

Keep under ~250 words unless asked for more detail.

## Tool usage
- sea_distance → distance
- calculate_emissions → CO₂
- web_search → carriers, services, feeder networks, disruptions
- Combine tools in one response when relevant.

"""

_agent = create_agent(
    model="anthropic:claude-sonnet-4-5",
    tools=[web_search, calculate_emissions, sea_distance],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=InMemorySaver(),
)


def run_agent(user_message: str, thread_id: str = "default") -> str:
    """Run the agent and return the full reply (non-streaming)."""
    config = {"configurable": {"thread_id": thread_id}}
    response = _agent.invoke(
        {"messages": [HumanMessage(content=user_message)]},
        config,
    )
    return response["messages"][-1].content


def stream_agent(user_message: str, thread_id: str = "default"):
    """Stream the agent's final text reply token-by-token."""
    config = {"configurable": {"thread_id": thread_id}}

    for chunk, _metadata in _agent.stream(
        {"messages": [HumanMessage(content=user_message)]},
        config,
        stream_mode="messages",
    ):
        # Skip tool messages (tool results from Tavily, etc.)
        if chunk.__class__.__name__ == "ToolMessage":
            continue

        # Only stream assistant text
        content = chunk.content
        if isinstance(content, str) and content:
            yield content
        elif isinstance(content, list):
            # Claude returns content as a list of blocks during tool use.
            # Only yield text blocks, skip tool_use blocks.
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if text:
                        yield text