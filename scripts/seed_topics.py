#!/usr/bin/env python3
"""
Seed or update topics.json interactively.
Usage: python scripts/seed_topics.py
"""

import sys
import json
sys.path.insert(0, __file__.rsplit("/scripts", 1)[0])

TOPICS_FILE = "data/topics.json"


def main():
    try:
        with open(TOPICS_FILE) as f:
            data = json.load(f)
    except Exception:
        data = {"topics": []}

    print(f"Current topics: {data['topics']}\n")
    print("Enter new topics one per line. Empty line to finish.")

    while True:
        topic = input("> ").strip()
        if not topic:
            break
        if topic not in data["topics"]:
            data["topics"].append(topic)
            print(f"  Added: {topic}")
        else:
            print(f"  Already tracked: {topic}")

    with open(TOPICS_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nSaved {len(data['topics'])} topics to {TOPICS_FILE}")


if __name__ == "__main__":
    main()
