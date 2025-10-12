#!/usr/bin/env python3
"""Test fuzzy matching through the full validate_citation function."""

from citations import validate_citation

# Paste your test strings here
ai_claimed_quote = """As of this writing, the top eight problem areas are: Risks from artificial intelligence, Catastrophic pandemics, Building effective altruism, Global priorities research, Nuclear war, and Improving decision making"""
source_1_text = """As of this writing, the top eight problem areas are:\n- Risks from artificial intelligence\n- Catastrophic pandemics\n- Building effective altruism\n- Global priorities research\n- Nuclear war\n- Improving decision making (especially in important institutions)\n- Climate change\n- Great power conflict\nWe’ve already given few examples of concrete ways to tackle these issues above.\nThe above list is provisional, and it is likely to change as we learn more. We also list many other pressing problems that we believe are highly important from a longtermist point of view, as well as a few that would be high priorities if we rejected longtermism.\nWe hope more people will challenge our ideas and help us think more clearly about them."""

source_2_text = """Another article about something else entirely."""

# Create fake source chunks (minimal objects with payload attribute)
class FakeChunk:
    def __init__(self, text, title="Test Article", url="https://example.com/test"):
        self.payload = {
            'text': text,
            'title': title,
            'url': url
        }

source_chunks = [
    FakeChunk(source_1_text, "Career Capital Article", "https://80000hours.org/career-capital"),
    FakeChunk(source_2_text, "Other Article", "https://80000hours.org/other"),
]

# Test validation (source_id is 1-indexed)
source_id_to_test = 1
result = validate_citation(ai_claimed_quote, source_chunks, source_id_to_test)

print(f"AI's claimed quote:\n\"{ai_claimed_quote}\"\n")
print(f"Source {source_id_to_test} text:\n\"{source_chunks[source_id_to_test-1].payload['text']}\"\n")
print(f"Valid: {result['valid']}")
print(f"Fuzzy Score: {result['fuzzy_match_score']:.1f}%")

if result['valid']:
    print(f"Matched Text: \"{result['matched_text']}\"")
    if result.get('remapped'):
        print(f"Remapped: source {result.get('original_source_id')} → {result['source_id']}")
else:
    print(f"Reason: {result['reason']}")
    if result.get('matched_text'):
        print(f"Closest Match: \"{result['matched_text']}\"")
