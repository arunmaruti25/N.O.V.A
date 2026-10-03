import asyncio
from backend.orchestrator import orchestrate_task

async def main():
    prompts = [
        "Open YouTube.",
        "Open Chrome and search YouTube for Minecraft.",
        "Open Notepad and type Hello NOVA.",
        "What's my battery percentage?",
        "Take a screenshot.",
    ]

    for p in prompts:
        print("=" * 60)
        print("INPUT:", p)
        res = await orchestrate_task(p)
        print("STATUS:", res.get("status"))
        print("ACTION:", res.get("action"))
        print("MODEL:", res.get("model_used"))
        print("VERIFIED:", res.get("verified"))
        print("RESPONSE:", res.get("response"))
        if res.get("tool_steps"):
            print("STEPS COUNT:", len(res["tool_steps"]))
        if res.get("audio_path"):
            print("AUDIO CREATED:", res["audio_path"] != "")

if __name__ == "__main__":
    asyncio.run(main())

