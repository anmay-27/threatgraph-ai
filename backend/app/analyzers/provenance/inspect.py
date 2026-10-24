import json
from pathlib import Path
from app.schemas.evidence import finding


def inspect_provenance(path: Path, asset: str):
    try:
        import c2pa
    except ImportError:
        return [
            finding(
                asset,
                "c2pa",
                "provenance",
                "unavailable",
                "C2PA SDK is not installed. Credential presence and validity are unknown.",
                metadata={"present": None, "valid": None},
            )
        ]
    try:
        # Never resolve remote manifests or fetch arbitrary credential URLs.
        context = c2pa.Context.from_dict({"verify": {"remote_manifest_fetch": False}})
        from app.analyzers.file.inspect import detect_mime

        mime = detect_mime(path.read_bytes()[:8192])
        with path.open("rb") as stream:
            with c2pa.Reader(mime, stream, context=context) as reader:
                store = json.loads(reader.json())
                state = reader.get_validation_state()
                results = reader.get_validation_results()
        active = store.get("manifests", {}).get(store.get("active_manifest"), {})
        valid = str(state).lower() in ("valid", "trusted")
        actions = [
            action
            for a in active.get("assertions", [])
            if a.get("label", "").startswith("c2pa.actions")
            for action in a.get("data", {}).get("actions", [])
        ]
        synthetic = any("trainedAlgorithmicMedia" in json.dumps(a) for a in actions)
        camera = any("digitalCapture" in json.dumps(a) for a in actions)
        trusted = str(state).lower() == "trusted"
        metadata = {
            "present": bool(active),
            "valid": valid,
            "trusted_signer": active.get("signature_info") if trusted else None,
            "claim_generator": active.get("claim_generator"),
            "actions": actions,
            "ingredients": active.get("ingredients", []),
            "validation_results": results,
            "state": str(state),
        }
        output = [
            finding(
                asset,
                "c2pa",
                "provenance",
                "valid_credential" if valid else "invalid_or_untrusted_credential",
                "Credential validity concerns provenance integrity, not whether the depicted event is true.",
                None if valid else 0.6,
                0.9,
                metadata=metadata,
            )
        ]
        if valid and synthetic:
            output.append(
                finding(
                    asset,
                    "c2pa",
                    "synthetic_media",
                    "declared_ai_generation",
                    "A valid signed claim declares algorithmically generated media.",
                    0.98,
                    0.95,
                    hypothesis="synthetic_media",
                )
            )
        elif trusted and camera:
            output.append(
                finding(
                    asset,
                    "c2pa",
                    "synthetic_media",
                    "trusted_camera_claim",
                    "A trusted signed claim declares digital camera capture.",
                    0.05,
                    0.9,
                    hypothesis="synthetic_media",
                )
            )
        return output
    except Exception as exc:
        message = str(exc)
        absent = any(
            x in message.lower()
            for x in ("jumbfnotfound", "manifestnotfound", "no jumbf", "no manifest")
        )
        return [
            finding(
                asset,
                "c2pa",
                "provenance",
                "not_present" if absent else "verification_unavailable",
                "No embedded credentials found; absence is neutral."
                if absent
                else "Credential inspection did not complete.",
                metadata={
                    "present": False if absent else None,
                    "valid": None,
                    "detail": message[:200],
                },
            )
        ]
