"""Recognize explicit, editable generation-workflow metadata; never proof."""
import json
import re


def generation_markers(info: dict, exif: dict) -> list[str]:
    markers = []
    parameters = str(info.get("parameters", ""))[:20000]
    if re.search(r"Steps:\s*\d+", parameters) and re.search(r"Seed:\s*\d+", parameters) and "Sampler:" in parameters:
        markers.append("PNG generation parameters (steps, sampler and seed)")
    for key in ("prompt", "workflow"):
        raw = info.get(key)
        if not isinstance(raw, str) or len(raw) > 100000:
            continue
        try:
            workflow = json.loads(raw)
        except (ValueError, TypeError):
            continue
        if isinstance(workflow, dict) and any(isinstance(node, dict) and node.get("class_type") in ("KSampler", "KSamplerAdvanced", "SamplerCustom", "SamplerCustomAdvanced") for node in workflow.values()):
            markers.append("Embedded diffusion sampling workflow")
    software = str(exif.get("Software", ""))[:300].lower()
    if any(name in software for name in ("stable diffusion", "comfyui", "automatic1111")):
        markers.append("EXIF software identifies an image-generation tool")
    return list(dict.fromkeys(markers))
