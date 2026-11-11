"""Conservative shape screening, not provider attribution or watermark verification."""
import cv2
import numpy as np


def corner_sparkles(image):
    """Return isolated four-point light shapes in bottom corners for manual review."""
    view = image.copy()
    view.thumbnail((1600, 1600))
    gray = cv2.cvtColor(np.asarray(view.convert('RGB')), cv2.COLOR_RGB2GRAY)
    height, width = gray.shape
    found = []
    for left, right in ((0, int(width * .2)), (int(width * .8), width)):
        top = int(height * .8)
        crop = gray[top:, left:right]
        for threshold in (70, 140, 210):
            _, mask = cv2.threshold(crop, threshold, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if not (.015 * width <= w <= .1 * width and .75 <= w / max(h, 1) <= 1.33):
                    continue
                if x == 0 or y == 0 or x+w >= crop.shape[1] or y+h >= crop.shape[0]:
                    continue
                area = cv2.contourArea(contour)
                if not .25 <= area / (w*h) <= .65:
                    continue
                points = contour[:, 0, :].astype(float)
                normalized = (points - [x, y]) / [max(w-1, 1), max(h-1, 1)]
                extremes = [normalized[np.argmin(normalized[:, 0])], normalized[np.argmax(normalized[:, 0])], normalized[np.argmin(normalized[:, 1])], normalized[np.argmax(normalized[:, 1])]]
                if any(abs(p[1]-.5) > .16 for p in extremes[:2]) or any(abs(p[0]-.5) > .16 for p in extremes[2:]):
                    continue
                # Curved star arms leave the diagonal quadrants mostly empty.
                filled = np.zeros((h, w), dtype=np.uint8)
                cv2.drawContours(filled, [contour - [x, y]], -1, 1, -1)
                if any(filled[int(h*a), int(w*b)] for a,b in ((.22,.22),(.22,.78),(.78,.22),(.78,.78))):
                    continue
                box = [(left+x)/width, (top+y)/height, w/width, h/height]
                if any(abs(box[0]-old[0]) < .02 and abs(box[1]-old[1]) < .02 for old in found):
                    continue
                found.append(box)
    return found[:4]
