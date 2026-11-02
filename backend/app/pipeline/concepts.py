"""What we ask SAM to look for. One short noun phrase per request.

Categories drive room.json and the architect:
- furniture: things the architect may keep, replace or move
- decor:     small items, cheap wins (swap, add, restyle)
- fixture:   fixed context (light sources, heating, doors); never replaced
- zone:      surfaces that are free space where new products can be placed
             (an empty balcony floor is an opportunity, not a gap)

Prompts name the whole object: SAM segments every instance of the phrase,
so "shelf" returns each board separately (T1 hit the 16-object cap).
Dropped after T1 on IMG_1184: "shelf", "bookcase" and "display cabinet"
("shelving unit" catches bookcases and cabinets as whole objects), "window"
and "door" (split into panes / kitchen cabinet doors, 16-object cap),
"kitchen cabinet" (13 doors, kitchen is out of scope).
"""

CONCEPTS: dict[str, str] = {
    # furniture
    "sofa": "furniture",
    "armchair": "furniture",
    "coffee table": "furniture",
    "side table": "furniture",
    "dining table": "furniture",
    "chair": "furniture",
    "tv stand": "furniture",
    "shelving unit": "furniture",
    "wardrobe": "furniture",
    # decor
    "lamp": "decor",
    "rug": "decor",
    "cushion": "decor",
    "curtain": "decor",
    "potted plant": "decor",
    "vase": "decor",
    "picture frame": "decor",
    "mirror": "decor",
    # appliances and fixtures (context only)
    "television": "fixture",
    "robot vacuum": "fixture",
    "coffee machine": "fixture",
    "radiator": "fixture",
    # free space for new products
    "floor": "zone",
    "balcony floor": "zone",
}
