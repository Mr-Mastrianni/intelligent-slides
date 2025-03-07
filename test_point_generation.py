"""
Test script to verify the slide point generation logic.
"""
from slide_deck_generator import SlideDeckGenerator
import json

# Create test outline for psychedelics and AI
test_outline = """
# The Intersection of Psychedelics and AI

## Neural Network Patterns
Examining similarities in neural activity patterns during psychedelic experiences and AI processing.

## Expanding Consciousness Models
Theories of consciousness expansion and parallels to AI models that push beyond initial programming.

## Breaking Default Modes
Disruption of the brain's "default mode network" during psychedelic experiences and parallels to AI.

## Therapeutic Applications
AI-guided psychedelic therapy for mental health treatment.
"""

# Generate slides
generator = SlideDeckGenerator()
slides = generator.generate_slides(test_outline)

# Print formatted output
print("Generated Slides:")
print("-" * 50)
for i, slide in enumerate(slides):
    print(f"\nSlide {i+1}: {slide.get('title')}")
    print(f"Content: {slide.get('content')}")
    print("Points:")
    for point in slide.get('points', []):
        print(f"  • {point}")
    print("-" * 50)

# Output as JSON for reference
with open("test_slides.json", "w") as f:
    json.dump(slides, f, indent=2)

print(f"\nJSON output saved to test_slides.json")
