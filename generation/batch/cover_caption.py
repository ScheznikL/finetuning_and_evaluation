# Prosthetic leg cover - Alleles-style below-knee shell parameters

MATERIAL = "hard plastic"
COLOR = "black"
FINISH = "non-reflective matte"
TEXTURE = "smooth with minor wear, scratches and scuffs"

TOTAL_LENGTH = 37.0          # overall height from top to bottom edge
TOP_WIDTH = 15.0             # approximate internal top opening width
BOTTOM_WIDTH = 11.0          # approximate internal bottom width
CHANNEL_DEPTH = 7.0          # depth of U-channel from open face to back
WALL_THICKNESS = 0.75        # average material thickness

TOP_NOTCH_WIDTH = 2.0        # centered rectangular recess at top
TOP_NOTCH_DEPTH = 1.0

# Rivet / bolt positions (distance from top edge, symmetric left/right)
RIVET_1_HEIGHT = 6.5
RIVET_2_HEIGHT = 16.5
RIVET_3_HEIGHT = 25.5
RIVET_DIAMETER = 1.0
RIVET_PROTRUSION = 0.5

# Mid-section horizontal clamp / pylon mount
CLAMP_HEIGHT_FROM_TOP = 20.5   # center of clamp
CLAMP_INTERNAL_DIAMETER = 3.5
CLAMP_LENGTH = 4.5             # along axis
CLAMP_PROTRUSION = 4.5         # outward from surface
CLAMP_SCREW_HOLE_COUNT = 2     # one on each tab
CLAMP_BASE_SCREWS = 2

# Additional features
STRAPS_COUNT = 2                 # top primary + bottom stabilizer
STRAP_MATERIAL = "polyurethane"
BUMPER = "foam"                  # at bottom contact point
COMPATIBILITY = "dynamic feet, expulsion valves, REVO sockets"

# Model generation flags
IS_HOLLOW = True
OPEN_BACK = True
STRUCTURE_RIGIDITY = "high"
OPTIONAL_PATTERN = "carbon fiber weave"

CAPTION = f"Create one {MATERIAL} below-knee prosthetic cover in a form of shell the style restores natural limb silhouette. Ergonomic semi-cylindrical U-shaped open channel.\
    Total length: {TOTAL_LENGTH} cm. Tapering U-channel: top internal width {TOP_WIDTH} cm, bottom internal width {BOTTOM_WIDTH} cm,\
    channel depth {CHANNEL_DEPTH} cm, wall thickness is {WALL_THICKNESS} cm. Centered rectangular top notch: {TOP_NOTCH_WIDTH} cm wide, {TOP_NOTCH_DEPTH} cm deep."

CAPTION_ankle = f"Create one {MATERIAL} transtibial prosthetic cover extending from the proximal calf to the distal ankle, in a form of shell, the style restores natural limb silhouette. Ergonomic semi-cylindrical U-shaped open channel.\
    Total length: {TOTAL_LENGTH} cm. Tapering U-channel: top internal width {TOP_WIDTH} cm, bottom internal width {BOTTOM_WIDTH} cm,\
    channel depth {CHANNEL_DEPTH} cm, wall thickness approx. {WALL_THICKNESS} cm.\
    Centered rectangular top notch: {TOP_NOTCH_WIDTH} cm wide, {TOP_NOTCH_DEPTH} cm deep."

# CAPTION = f"High-resolution 3D model of a {MATERIAL} below-knee prosthetic leg cover shell \
#     the style restores natural limb silhouette. Ergonomic semi-cylindrical U-shaped open channel  \
#     Total length: {TOTAL_LENGTH} cm. \
#     Tapering U-channel: top internal width {TOP_WIDTH} cm, bottom internal width {BOTTOM_WIDTH} cm, \
#     channel depth {CHANNEL_DEPTH} cm, wall thickness approx. {WALL_THICKNESS} cm. \
#     Centered rectangular top notch: {TOP_NOTCH_WIDTH} cm wide, {TOP_NOTCH_DEPTH} cm deep. "
   # "Three symmetric pairs of metallic rivets/bolt heads (1 cm diameter, 0.5 cm protrusion) for strap attachment "
   # f"at heights from top: {RIVET_1_HEIGHT} cm, {RIVET_2_HEIGHT} cm, {RIVET_3_HEIGHT} cm. "
   # f"Mid-section horizontal pylon clamp mount centered at approx. {CLAMP_HEIGHT_FROM_TOP} cm from top, "
    #f"protruding {CLAMP_PROTRUSION} cm outward, with internal diameter {CLAMP_INTERNAL_DIAMETER} cm, "
   # f"length {CLAMP_LENGTH} cm, two side screw holes and two base attachment screws. "
   # "Designed for two polyurethane straps (top primary, bottom stabilizer) with foam bumper at bottom contact. "
   # "Fully hollow, open-backed structure for socket fit, high rigidity, compatible with dynamic prosthetic feet, "
   # "expulsion valves and REVO-style sockets. Optional subtle carbon fiber weave pattern on surface. "
   # "Non-reflective matte black finish, smooth curved ergonomic contours, precise medical-grade appearance."
#"with smooth interior and exterior, minor realistic wear scratches and scuffs. "
#CAPTION = "Matte black below-knee prosthetic leg cover shell - ergonomic U-channel design with pylon clamp and strap mounts"


''' Prompt for 100 promts:
100 prompts that can be easiely acsessed by python script.
the prompt structure must be following:
CAPTION = f"Create one {MATERIAL} below-knee prosthetic cover in a form of shell the style restores natural limb silhouette. Ergonomic semi-cylindrical U-shaped open channel.\

    Total length: {TOTAL_LENGTH} cm. Tapering U-channel: top internal width {TOP_WIDTH} cm, bottom internal width {BOTTOM_WIDTH} cm,\

    channel depth {CHANNEL_DEPTH} cm, wall thickness is {WALL_THICKNESS} cm. Centered rectangular top notch: {TOP_NOTCH_WIDTH} cm wide, {TOP_NOTCH_DEPTH} cm deep."

The sentance before first '\' must change: prompt may include different customization approaches of prosthetic cover design like different textures and replication of materials. 

Part that describes sizes and measurmets "Total length: {TOTAL_LENGTH} cm. Tapering U-channel: top internal width {TOP_WIDTH} cm, bottom internal width {BOTTOM_WIDTH} cm,\

    channel depth {CHANNEL_DEPTH} cm, wall thickness is {WALL_THICKNESS} cm. Centered rectangular top notch: {TOP_NOTCH_WIDTH} cm wide, {TOP_NOTCH_DEPTH} cm deep." -  have to stay the same and only variables in '{...}' must change but to reasonable extend taking following data in consideration: 

'''