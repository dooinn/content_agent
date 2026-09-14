"""Prompt templates. Context goes in XML-tagged JSON so data stays distinct from instructions."""

import json
from typing import Any

from app.domain.length import PROFILES, WORDS_PER_MINUTE, LengthProfile

SHORT = PROFILES[30]

SYSTEM = """You are the writers' room behind a channel of vertical history videos, from \
30-second shorts to 3-minute stories. Each video tells one surprising, true story about a \
historical figure.

Standards:
- Accuracy first. Never present a legend or a disputed claim as settled fact.
- Specific beats generic: names, numbers, places, objects.
- Write in natural, contemporary English.
- A human producer reviews every stage, so keep outputs easy to scan and edit."""


def _tag(name: str, value: Any) -> str:
    body = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False)
    return f"<{name}>\n{body}\n</{name}>"


def _guidance(
    feedback: str | None,
    previous: Any = None,
    review: dict | None = None,
    reviewer: str = "reviewer",
) -> str:
    """Producer direction and reviewer findings, appended to a writing prompt."""
    parts = []
    if previous is not None and (feedback or review):
        parts.append("This is a revision of the previous draft.")
        parts.append(_tag("previous_draft", previous))
    if review:
        parts.append(f"A {reviewer} flagged these problems in the previous draft. Fix every one.")
        parts.append(_tag("review", review))
    if feedback:
        parts.append(_tag("producer_direction", feedback))
        if previous is not None:
            parts.append("Follow the producer's direction and keep what they did not object to.")
        else:
            parts.append("Follow the producer's direction.")
    return "\n\n" + "\n\n".join(parts) if parts else ""


# ---------------------------------------------------------------- research


def research(topic: str, feedback: str | None, length: LengthProfile = SHORT) -> str:
    low, high = length.facts
    return f"""Research this historical figure for {length.adjective} video: {topic}

Use web search. Prefer peer-reviewed and academic work, major encyclopedias, museums, archives, \
and official heritage sites. Use blogs, listicles, Q&A sites, and social media only as leads to \
confirm elsewhere.

Collect:
1. Basics: full name, birth and death dates, era, region, and a two-sentence biography.
2. {low} to {high} surprising, lesser-known, story-worthy episodes or facts. For each, judge \
whether it is well documented, disputed, or legend, and note competing accounts.
3. Appearance: what contemporary portraits and descriptions say about how they looked, \
including at different ages.
4. Material culture: clothing, hair, accessories, and the architecture, objects, and \
landscapes of their world.

Write compact research notes under those four headings, and say what kind of publication each \
source is.{_guidance(feedback)}"""


def fact_sheet(topic: str, notes: str, sources: list[dict]) -> str:
    return f"""Convert these research notes on {topic} into a fact sheet.

Rules:
- Cite only ids from the source list. Every fact needs at least one source id unless its \
status is "legend".
- Give every cited source a tier: scholarly, reference, or popular.
- "verified" requires at least one scholarly or reference source that clearly supports the \
claim. Facts backed only by popular sources are at most "disputed".
- Keep claims atomic: one fact per claim.
- death_year is the integer year of death (negative for BCE), or null if living or unknown.
- In `sources`, include only the sources that facts cite, with ids, titles, and urls copied \
exactly from the list.

{_tag("source_list", sources)}

{_tag("research_notes", notes)}"""


def fact_check(kind: str, draft: Any, sheet: dict) -> str:
    return f"""Fact-check this {kind} against the fact sheet, which is the only accepted source \
of truth.

{_tag("draft", draft)}

{_tag("fact_sheet", sheet)}

Check every factual claim: names, numbers, ages, dates, places, events, and cause-and-effect \
statements. Flag a claim when:
- not_in_fact_sheet: the fact sheet does not support it, even if it may be true elsewhere
- contradicts_fact_sheet: it conflicts with the fact sheet
- overstates_certainty: it states a disputed or legendary fact, or a "likely" interpretation, \
as settled

Rhetorical framing, emotional language, and scene-setting that make no factual claim are fine. \
Set passed to true only when there are no issues. Every suggested_fix must be a concrete \
rewrite."""


# ---------------------------------------------------------------- story


def angles(
    sheet: dict,
    feedback: str | None,
    previous: Any,
    review: dict | None = None,
    length: LengthProfile = SHORT,
) -> str:
    return f"""Propose three distinct story angles for {length.adjective} video about \
{sheet["figure"]}.

A strong angle:
- Has this shape: {length.structure}
- Draws on enough fact-sheet material to fill {length.label} without padding or repetition.
- Opens with a hook line of at most 12 words that makes a scrolling viewer stop. \
Never open with "Did you know".
- Uses only claims found in the fact sheet, and rests on verified facts. Disputed material is \
fine only if the narration can frame it honestly.
- Ends on a payoff that recontextualizes the hook.

Make the three angles differ in tone, for example ironic, dramatic, and human.

{_tag("fact_sheet", sheet)}{_guidance(feedback, previous, review, "fact checker")}"""


def script(
    sheet: dict,
    angle: dict,
    feedback: str | None,
    previous: Any,
    review: dict | None = None,
    length: LengthProfile = SHORT,
) -> str:
    words, segments, segment_words = length.words, length.segments, length.segment_words
    scene_low, scene_high = length.scene_seconds
    if length.seconds <= 30:
        pacing = "A beat may span two segments."
    else:
        pacing = (
            "A beat may span several segments. Spend most of them on setup and twist, where "
            "every segment adds a new detail or complication; never repeat a point."
        )
    return f"""Write the narration for {length.adjective} vertical video.

{_tag("angle", angle)}

{_tag("fact_sheet", sheet)}

Requirements:
- {words[0]} to {words[1]} words in total. It will be read at about {WORDS_PER_MINUTE} words \
per minute.
- Story shape: {length.structure}
- {segments[0]} to {segments[1]} segments. Each segment becomes one on-screen scene of about \
{scene_low} to {scene_high} seconds, so keep each to {segment_words[0]}-{segment_words[1]} words.
- Beats in order: hook (first segment, at most 12 words, starts mid-action or with a startling \
claim), setup, twist, payoff, closer (lands the irony or meaning; no call to action). {pacing}
- Spoken English: short sentences, active voice, concrete images. Write numbers and dates the \
way a narrator would say them.
- Use only claims found in the fact sheet. List the fact ids each segment relies on. Frame \
disputed claims honestly ("legend says", "historians still argue").
- Every segment must suggest a clear image.\
{_guidance(feedback, previous, review, "fact checker")}"""


# ---------------------------------------------------------------- audio


def music(narration: str, angle: dict, seconds: int, feedback: str | None) -> str:
    return f"""Write a music-generation prompt for a {seconds}-second instrumental bed under \
this narration.

{_tag("narration", narration)}

{_tag("angle", {"title": angle["title"], "logline": angle["logline"]})}

The track must be instrumental with no vocals, stay sparse in the voice range so narration \
stays clear, and follow the story's arc: tension under the hook, a build into the twist, release \
at the payoff. Evoke the era through instrumentation while sounding like modern cinematic \
scoring. State genre, mood, instruments, and tempo in at most 400 characters.\
{_guidance(feedback)}"""


# ---------------------------------------------------------------- visuals


def bible(
    sheet: dict,
    angle: dict,
    script_data: dict,
    feedback: str | None,
    previous: dict | None,
    has_style_reference: bool = False,
) -> str:
    if has_style_reference:
        style_line = (
            "- The attached image is the producer's style reference. Describe its rendering "
            "style precisely in visual_style, color_palette, and lighting: medium, character "
            "proportions, surface materials, lighting, lens, and depth of field. Take only the "
            "style; ignore its subject, era, and setting."
        )
    else:
        style_line = (
            "- Default style: cinematic painterly realism, like concept art for a high-end "
            "historical drama, unless the story clearly calls for something else."
        )
    return f"""Create the visual bible for this short. Every image is generated from it, so it \
must produce one consistent look.

{_tag("fact_sheet", sheet)}

{_tag("angle", angle)}

{_tag("script", script_data)}

Guidelines:
{style_line}
- Ground each look in the fact sheet's appearance notes, at the age the story shows.
- Period details must fit the era and region. List anachronisms an image model is likely to \
slip in, such as wrong uniforms, modern glass, zippers, or later weapons.
- character.looks: one look for each clearly different age or costume the script puts on \
screen. Most stories need exactly one. Add another only when the story shows the person at a \
very different age or in a completely different role. Use ids such as "young" or "mature".
- Each look's sheet_prompt: one vertical full-body reference portrait of that look, standing in \
a neutral three-quarter pose, face clearly visible, period-accurate costume, plain muted studio \
backdrop, soft even lighting, in the bible's style, no text.{_guidance(feedback, previous)}"""


def _reference_roles(has_character: bool, has_style: bool) -> str:
    """Explain what each attached reference image is for, in the order they are sent."""
    roles = []
    if has_character:
        roles.append("the character reference. Keep this person's face, hair, build, and "
                     "costume consistent")
    if has_style:
        roles.append("the style reference. Use it only as a style guide: match its rendering "
                     "style, character proportions, surface materials, lighting, and camera "
                     "feel. Do not copy its subject, clothing, setting, or composition")
    lines = [f"Reference image {i} is {role}." for i, role in enumerate(roles, start=1)]
    return "\n".join(lines) + "\n\n" if lines else ""


def character_sheet_image(bible_data: dict, look: dict, has_style_reference: bool = False) -> str:
    return _reference_roles(False, has_style_reference) + (
        f"{look['sheet_prompt']} Style: {bible_data['visual_style']}. "
        f"Palette: {bible_data['color_palette']}. No text, no watermark."
    )


def scenes(
    script_data: dict,
    timings: list[dict],
    bible_data: dict,
    sheet: dict,
    critic_report: dict | None,
    feedback: str | None,
    previous: list[dict] | None,
) -> str:
    segments = [
        {"order": t["order"], "seconds": round(t["end"] - t["start"], 1), **segment}
        for t, segment in zip(timings, script_data["segments"], strict=True)
    ]
    world_fields = ("era", "region", "appearance_notes", "costume_notes", "setting_notes")
    world = {k: sheet[k] for k in world_fields}
    character = bible_data["character"]
    look_fields = ("id", "label", "age", "costume")
    looks = [{k: look[k] for k in look_fields} for look in character["looks"]]
    guidance = _guidance(feedback, previous, critic_report, "historical and VFX reviewer")
    return f"""Write one scene for each narration segment. Scene N visualizes segment N.

{_tag("segments", segments)}

{_tag("visual_bible", bible_data)}

{_tag("world", world)}

{_tag("character_looks", looks)}

For each scene:
- description: 2-3 sentences on subject and action, setting, composition, lighting, and mood. \
Show the idea of the narration rather than illustrating it word by word.
- shot_type: vary shots across scenes. Scene 1 must be the most arresting image.
- camera_move: one subtle move for later animation, such as a slow push-in or a gentle pan.
- character_look: the id of the look shown when {character["name"]} is visible, or null. Each \
look has its own reference image, so choose the look whose age and costume match that moment. \
If a moment needs a look that is not listed, keep the character off screen and show objects, \
places, or paintings instead.
- image_prompt: a self-contained prompt for a vertical 9:16 frame. Lead with subject and action, \
then setting, composition, lighting, and the bible's style. When character_look is set, \
refer to "the character from reference image 1" and restate that look's costume. Keep the \
subject out of the bottom third, which carries captions. Never ask for text, captions, \
signage, logos, or watermarks. Avoid gore and nudity.{guidance}"""


def critic(scenes_data: list[dict], script_data: dict, bible_data: dict, sheet: dict) -> str:
    return f"""Review these scene drafts as both a historical consultant and a VFX supervisor.

{_tag("scenes", scenes_data)}

{_tag("script", script_data)}

{_tag("visual_bible", bible_data)}

{_tag("fact_sheet", sheet)}

Each character look in the visual bible has its own reference image; a scene uses the one named \
in its character_look.

Flag only problems that would visibly hurt the video:
- anachronism: clothing, objects, architecture, or technology wrong for {sheet["era"]}, \
{sheet["region"]}
- continuity: visual style inconsistent with the bible or other scenes
- fact_mismatch: an image contradicts the fact sheet or its own narration
- character_reference: the chosen character_look does not match the age or costume that moment \
needs, the prompt describes a different age or costume than the chosen look, or the character \
is visible while character_look is null
- bible_rule: the scene breaks a rule or exception written in the visual bible
- prompt_quality: vague subject, conflicting instructions, requests for text, or the subject \
placed in the bottom third
- safety: gore, nudity, or anything an image model would refuse

Set passed to true only when nothing is worth fixing. Every suggested_fix must be concrete \
enough to apply directly."""


def keyframe_image(
    scene: dict, feedback: str | None, has_character_reference: bool, has_style_reference: bool
) -> str:
    prompt = _reference_roles(has_character_reference, has_style_reference) + scene["image_prompt"]
    return f"{prompt}\nProducer note: {feedback}" if feedback else prompt


# ---------------------------------------------------------------- video


def motion(
    scenes_data: list[dict], bible_data: dict, feedback: str | None, previous: Any
) -> str:
    shot_fields = ("order", "clip_seconds", "narration", "description", "shot_type", "camera_move")
    shots = [{k: scene.get(k) for k in shot_fields} for scene in scenes_data]
    return f"""Write an image-to-video motion prompt for each scene of a vertical short. Each \
scene's keyframe becomes the first frame of its clip and already fixes the composition, people, \
costumes, lighting, and style, so describe only what moves.

{_tag("scenes", shots)}

{_tag("visual_style", bible_data["visual_style"])}

For each scene's video_prompt:
- One clear primary motion and one camera move, paced to fill clip_seconds.
- Subtle, physically plausible motion. Faces, hands, and costumes stay consistent with the \
first frame, and no new people or objects appear.
- Add ambient life where it fits: candle flicker, drifting dust, fabric sway, breathing.
- Paintings and sculptures stay still; move only the camera and the light around them.
- Keep the first frame's style. No cuts, no text, no morphing or sudden transformations.
- One to three present-tense sentences.{_guidance(feedback, previous)}"""


def clip_prompt(scene: dict, feedback: str | None) -> str:
    prompt = scene["video_prompt"]
    return f"{prompt}\nProducer note: {feedback}" if feedback else prompt
