import numpy as np

SOURCES = [
    "url_detector",
    "reputation",
    "webpage",
    "image_detector",
    "audio_detector",
    "video_detector",
    "c2pa",
    "file_inspector",
    "clamav",
]
FEATURE_NAMES = [
    f"{source}_{field}"
    for source in SOURCES
    for field in ("score", "present", "uncertainty")
] + ["conflict_count", "ood_fraction"]


def vector(evidence, conflict_list, include_conflicts=True, include_uncertainty=True):
    values = []
    for source in SOURCES:
        scored = [e for e in evidence if e.source == source and e.score is not None]
        values.extend(
            [
                max((e.score for e in scored), default=0.5),
                float(bool(scored)),
                max((e.uncertainty for e in scored), default=1)
                if include_uncertainty
                else 0.0,
            ]
        )
    values.extend(
        [
            min(len(conflict_list), 10) / 10 if include_conflicts else 0.0,
            sum(
                e.metadata.get("ood") == "possibly_out_of_distribution"
                for e in evidence
            )
            / max(1, len(evidence))
            if include_uncertainty
            else 0.0,
        ]
    )
    return np.asarray(values, dtype=np.float32)
