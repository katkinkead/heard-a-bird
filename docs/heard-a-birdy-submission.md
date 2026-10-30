# Heard a Birdy — submission draft

30 October 2026. Checked against the local repository and project iteration history. Rubric B's wording has not been supplied or located, so exact rubric alignment remains unverified.

## Short description

Heard a Birdy (Songsketch) turns birdsong into a living artwork and a growing record of your garden. Designed for gardeners and nature-curious households, it identifies birds by sound and records when and how often each species is heard. Birds gradually paint themselves onto a branching composition, while a companion dashboard lets you explore species history, separate bouts of activity and how much time the system was actually listening.

It makes the wildlife around your home more visible, memorable and understandable. The next step is richer insight into daily rhythms, returning visitors and seasonal changes within each garden. Longer term, the ambition is an opt-in network of gardens contributing observations to a larger regional dataset, connecting personal curiosity with a broader understanding of local birdlife.

## Evidence of iteration

- **From generic bird pictures to a coherent visual language.** Early concepts were too cute, busy or literal. Reference studies and repeated critique shaped 45 species illustrations with recognisable anatomy, subtle caricature, textured pigment and restrained geometry. I documented a reusable style system that preserves consistency while leaving room for each bird's character.
- **From revealing an image to watching it be painted.** Early animation felt like an opaque layer being erased. Studies of painting techniques informed sketch marks, changing stroke weight, pigment spread and a detailed pencil-like finish. I shortened the sequence from 90 to 75 seconds, redistributed visible progress and improved final-frame clarity against the approved artwork.
- **From one portrait to a living garden.** Branch mockups exposed repetitive shapes, crowded birds and cramped captions. I developed a locally generated branching system that scales as species appear, with new limbs for busy periods. Names, counts and live-status marks wait until the painting finishes, keeping attention on the drawing.
- **From raw detections to interpretable observations.** I separated repeated classifier matches from bouts of activity, garden unusualness from regional rarity, and quiet listening from missing data. The dashboard now exposes those distinctions and their supporting evidence. Reviewing it revealed the next opportunity: turning records into clearer local patterns and comparisons before expanding to a regional network.
- **From an attractive demo to a testable system.** I ran real BirdNET on recorded owl audio in a virtual Linux environment and tested its delivery into the server. Separate simulations exercised duplicate messages, outages and recovery. These trials informed timestamp handling, counting and health indicators; physical outdoor validation remains ahead.
- **From software to an approachable object.** I iterated an illustrated setup journey and a hanging glass-and-metal bird enclosure concept, refining service access and microphone shelter. The product hardware brief now requires replaceable audio hardware and local BirdNET operation, while leaving processor selection open to evidence. The enclosure and custom PCB remain design work, not manufactured hardware.
