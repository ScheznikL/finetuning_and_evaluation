size_chart = {
    'S': {
        'length': (35.0, 40.99),
        'ankle_circ': (19.0, 21.99),
        'calf_circ': (30.0, 34.99)
    },
    'M': {
        'length': (41.0, 45.99),
        'ankle_circ': (22.0, 24.99),
        'calf_circ': (35.0, 38.99)
    },
    'L': {
        'length': (46.0, 50.99),
        'ankle_circ': (25.0, 27.99),
        'calf_circ': (39.0, 42.99)
    }
}

design_templates = [
    # --- PLASTICS & BASICS (1-10) ---
    "Create one Matte White PLA below-knee prosthetic cover in a form of shell the style restores natural limb silhouette.",
    "Create one Glossy Black ABS below-knee prosthetic cover in a form of shell the style restores natural limb silhouette.",
    "Create one Translucent Blue PETG below-knee prosthetic cover in a form of shell the style restores natural limb silhouette.",
    "Create one Recycled Grey Plastic below-knee prosthetic cover with a speckled texture.",
    "Create one High-visibility Orange Nylon below-knee prosthetic cover for active wear.",
    "Create one Smooth Beige Polycarbonate below-knee prosthetic cover matching skin tone.",
    "Create one Frosted Clear Resin below-knee prosthetic cover in a form of shell the style restores natural limb silhouette.",
    "Create one Rough Sandstone-finish PLA below-knee prosthetic cover with a tactile grip.",
    "Create one Pastel Pink ASA below-knee prosthetic cover with a soft-touch coating.",
    "Create one Neon Green TPU below-knee prosthetic cover with a flexible, rubberized finish.",

    # --- CARBON FIBER & COMPOSITES (11-20) ---
    "Create one Woven Carbon Fiber below-knee prosthetic cover with a high-gloss clear coat.",
    "Create one Forged Carbon Fiber below-knee prosthetic cover with a marbled black texture.",
    "Create one Matte Carbon Fiber below-knee prosthetic cover in a form of shell the style restores natural limb silhouette.",
    "Create one Kevlar-reinforced below-knee prosthetic cover with a yellow-black weave pattern.",
    "Create one Fiberglass below-knee prosthetic cover painted in a metallic automotive red.",
    "Create one Graphene-infused composite below-knee prosthetic cover in a form of shell the style restores natural limb silhouette.",
    "Create one Basalt Fiber below-knee prosthetic cover with a natural brownish-gold weave.",
    "Create one Lightweight Honeycomb Composite below-knee prosthetic cover exposed structure.",
    "Create one Black Alcantara-wrapped below-knee prosthetic cover for a premium automotive feel.",
    "Create one Epoxy Resin below-knee prosthetic cover with embedded gold leaf flakes.",

    # --- METALS & METALLICS (21-30) ---
    "Create one Polished Titanium below-knee prosthetic cover with a mirror finish.",
    "Create one Brushed Aluminum below-knee prosthetic cover with an industrial aesthetic.",
    "Create one Gold-plated below-knee prosthetic cover with an ornate luxury engraving.",
    "Create one Copper Patina below-knee prosthetic cover showing aged green oxidation details.",
    "Create one Rusty Iron texture below-knee prosthetic cover for a post-apocalyptic look.",
    "Create one Chrome-finished below-knee prosthetic cover in a form of shell the style restores natural limb silhouette.",
    "Create one Gunmetal Grey Steel below-knee prosthetic cover with a matte tactical finish.",
    "Create one Anodized Red Aluminum below-knee prosthetic cover with a scratch-resistant surface.",
    "Create one Bronze Cast below-knee prosthetic cover with a heavy, antique texture.",
    "Create one Iridescent Bismuth-style below-knee prosthetic cover with geometric metallic crystals.",

    # --- PATTERNS & LATTICES (31-40) ---
    "Create one Voronoi Pattern below-knee prosthetic cover with organic cellular holes.",
    "Create one Hexagonal Mesh below-knee prosthetic cover in a form of shell the style restores natural limb silhouette.",
    "Create one Triangular Lattice below-knee prosthetic cover optimized for lightweight strength.",
    "Create one Gyroid Infill structure below-knee prosthetic cover exposed as the outer surface.",
    "Create one Spiral Vase mode below-knee prosthetic cover with continuous fluid ridges.",
    "Create one Diamond Knurled texture below-knee prosthetic cover for enhanced grip.",
    "Create one Perforated Sheet Metal style below-knee prosthetic cover with circular vents.",
    "Create one Woven Basket texture below-knee prosthetic cover made of synthetic brown polymer.",
    "Create one Low-Poly geometric below-knee prosthetic cover with sharp faceted angles.",
    "Create one Wave Pattern below-knee prosthetic cover mimicking ocean ripples in blue plastic.",

    # --- BIO-ORGANIC & NATURE (41-50) ---
    "Create one Wood-grain PLA below-knee prosthetic cover resembling dark walnut.",
    "Create one Bamboo texture below-knee prosthetic cover with natural vertical striations.",
    "Create one Snake Scale texture below-knee prosthetic cover in a shimmering green gradient.",
    "Create one Human Muscle anatomy style below-knee prosthetic cover showing stylized red fibers.",
    "Create one Bone texture below-knee prosthetic cover looking like a natural skeletal extension.",
    "Create one Tree Bark texture below-knee prosthetic cover with rough, organic grooves.",
    "Create one Floral relief below-knee prosthetic cover with embossed rose patterns.",
    "Create one Coral Reef texture below-knee prosthetic cover with porous organic details.",
    "Create one Chitin Armor below-knee prosthetic cover resembling a beetle shell.",
    "Create one Marble Stone below-knee prosthetic cover with grey veins on white.",

    # --- SCI-FI & CYBERPUNK (51-60) ---
    "Create one Cyberpunk style below-knee prosthetic cover with neon yellow circuit lines.",
    "Create one Android White below-knee prosthetic cover with black panel lines.",
    "Create one Steampunk below-knee prosthetic cover with faux gears and copper pipes.",
    "Create one Sci-Fi Armor below-knee prosthetic cover with distressed battle damage.",
    "Create one Transparent OLED style below-knee prosthetic cover with digital glitch graphics.",
    "Create one Mech-Suit below-knee prosthetic cover with hydraulic piston details.",
    "Create one Tron-style below-knee prosthetic cover with glowing blue light strips.",
    "Create one Industrial Hazard below-knee prosthetic cover with yellow and black caution stripes.",
    "Create one Starship Hull below-knee prosthetic cover with grey plating and rivets.",
    "Create one Alien Biotech below-knee prosthetic cover with pulsing purple veins.",

    # --- ARTISTIC & FASHION (61-70) ---
    "Create one Denim Fabric texture below-knee prosthetic cover with stitching details.",
    "Create one Leather-wrapped below-knee prosthetic cover in brown with brass studs.",
    "Create one Graffiti Art below-knee prosthetic cover with vibrant street-style spray paint.",
    "Create one Watercolor Splash below-knee prosthetic cover with blending pastel hues.",
    "Create one Mosaic Tile below-knee prosthetic cover with small colorful ceramic squares.",
    "Create one Tattoo Ink style below-knee prosthetic cover featuring traditional dragon art.",
    "Create one Quilted Fabric texture below-knee prosthetic cover in a luxury diamond pattern.",
    "Create one Porcelain Doll style below-knee prosthetic cover with cracks and floral paint.",
    "Create one Velvet texture below-knee prosthetic cover in deep royal purple.",
    "Create one Camouflage print below-knee prosthetic cover in woodland green patterns.",

    # --- EXPERIMENTAL & ABSTRACT (71-80) ---
    "Create one Glitch Art below-knee prosthetic cover with distorted geometry.",
    "Create one Liquid Metal below-knee prosthetic cover appearing to melt chrome.",
    "Create one Crystal Shard below-knee prosthetic cover with jagged transparent spikes.",
    "Create one Foam Bubble texture below-knee prosthetic cover with a porous surface.",
    "Create one Origami Fold below-knee prosthetic cover appearing made of folded paper.",
    "Create one Wireframe below-knee prosthetic cover made of thin black scaffolding.",
    "Create one Pixel Art below-knee prosthetic cover with a voxel block construction.",
    "Create one Abstract Expressionist below-knee prosthetic cover with chaotic paint splatters.",
    "Create one Optical Illusion below-knee prosthetic cover with black and white stripes.",
    "Create one Fur texture below-knee prosthetic cover (synthetic) in a short black pile.",

    # --- COLOR VARIATIONS (81-90) ---
    "Create one Gradient Fade below-knee prosthetic cover transitioning from red to blue.",
    "Create one Metallic Gold below-knee prosthetic cover in a form of shell the style restores natural limb silhouette.",
    "Create one Metallic Silver below-knee prosthetic cover in a form of shell the style restores natural limb silhouette.",
    "Create one Matte Olive Green below-knee prosthetic cover tactical style.",
    "Create one Deep Navy Blue below-knee prosthetic cover with a satin finish.",
    "Create one Vibrant Crimson Red below-knee prosthetic cover with a gloss finish.",
    "Create one Canary Yellow below-knee prosthetic cover with a matte finish.",
    "Create one Pure White Minimalist below-knee prosthetic cover in a form of shell.",
    "Create one Jet Black Stealth below-knee prosthetic cover with light-absorbing texture.",
    "Create one Hot Pink below-knee prosthetic cover with a glitter texture.",

    # --- TEXTURE SPECIFIC (91-100) ---
    "Create one Sandblasted Metal below-knee prosthetic cover with a matte grey grain.",
    "Create one Hammered Copper below-knee prosthetic cover with dimpled texture.",
    "Create one Knitted Wool texture below-knee prosthetic cover scanned 3D surface.",
    "Create one Cork texture below-knee prosthetic cover with natural brown spotting.",
    "Create one Slate Rock below-knee prosthetic cover with layered stone texture.",
    "Create one Ice texture below-knee prosthetic cover translucent with internal cracks.",
    "Create one Lava Rock below-knee prosthetic cover black with glowing red cracks.",
    "Create one Damascene Steel below-knee prosthetic cover with wavy metal patterns.",
    "Create one Terrazzo Stone below-knee prosthetic cover with colorful embedded chips.",
    "Create one Carbon Kevlar Hybrid below-knee prosthetic cover with red and black weave."
]
