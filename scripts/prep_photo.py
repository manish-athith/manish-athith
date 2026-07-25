#!/usr/bin/env python3
"""
prep_photo.py — turn a portrait photo into a clean, high-contrast,
white-background grayscale image ready for ASCII conversion.

Steps:
  1. Isolate the subject. If the source image already carries real
     alpha transparency (e.g. a pre-cutout profile picture), that alpha
     channel is used directly — it's cleaner than anything re-derived
     from the flattened RGB. Otherwise falls back to OpenCV GrabCut
     (foreground/background segmentation seeded from a centered rect).
     Swap in `rembg` here for ML-based segmentation if you'd rather —
     GrabCut is used so this script has no heavy model download.
  2. Boost contrast with a global percentile stretch + gamma brighten
     so a flatly-lit face gets real highlights and shadows.
  3. Composite the isolated subject onto pure white so the background
     maps to the blank end of the ASCII ramp (white -> spaces).

Usage: python3 prep_photo.py source-photo.png
Output: source-prepped.png (grayscale)
"""
import sys
import cv2
import numpy as np
from PIL import Image


def _grabcut_mask(img):
    h, w = img.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    # Seed rect: tighter margin around the subject — portrait framing
    # assumption is subject centered, but busy backgrounds (car seats,
    # furniture) need a snugger box or GrabCut latches onto them.
    margin_x, margin_top, margin_bot = int(w * 0.14), int(h * 0.02), int(h * 0.10)
    rect = (margin_x, margin_top, w - 2 * margin_x, h - margin_top - margin_bot)

    cv2.grabCut(img, mask, rect, bgd_model, fgd_model, 6, cv2.GC_INIT_WITH_RECT)

    # Mark a thin border strip as definite background and a small
    # centered core as definite foreground, then refine with a couple
    # more iterations using GC_INIT_WITH_MASK — this cleans up patches
    # of background that GrabCut initially scored as probable-foreground.
    border = max(4, int(min(h, w) * 0.015))
    mask[:border, :] = cv2.GC_BGD
    mask[-border:, :] = cv2.GC_BGD
    mask[:, :border] = cv2.GC_BGD
    mask[:, -border:] = cv2.GC_BGD
    cy0, cy1 = int(h * 0.15), int(h * 0.75)
    cx0, cx1 = int(w * 0.30), int(w * 0.70)
    core = mask[cy0:cy1, cx0:cx1]
    core[(core == cv2.GC_PR_BGD)] = cv2.GC_PR_FGD
    mask[cy0:cy1, cx0:cx1] = core

    cv2.grabCut(img, mask, None, bgd_model, fgd_model, 4, cv2.GC_INIT_WITH_MASK)

    fg_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

    # Keep only the largest connected component (the person), drop
    # any small isolated background blobs GrabCut misclassified.
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(fg_mask, connectivity=8)
    if num_labels > 1:
        largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        fg_mask = np.where(labels == largest, 255, 0).astype(np.uint8)
    return fg_mask


def prep(path_in, path_out):
    pil_im = Image.open(path_in)
    has_alpha = pil_im.mode in ("RGBA", "LA") or (pil_im.mode == "P" and "transparency" in pil_im.info)

    if has_alpha:
        rgba = np.array(pil_im.convert("RGBA"))
        img = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2BGR)
        fg_mask = (rgba[:, :, 3] > 127).astype(np.uint8) * 255
    else:
        img = cv2.imread(path_in)
        if img is None:
            raise SystemExit(f"could not read {path_in}")
        fg_mask = None

    h, w = img.shape[:2]
    max_dim = 900 if has_alpha else 700
    scale = min(1.0, max_dim / max(h, w))
    if scale < 1.0:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        if fg_mask is not None:
            fg_mask = cv2.resize(fg_mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_AREA)
        h, w = img.shape[:2]

    if fg_mask is None:
        fg_mask = _grabcut_mask(img)

    # Clean up the mask: close small holes, smooth edges
    kernel = np.ones((7, 7), np.uint8)
    fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
    fg_mask = cv2.GaussianBlur(fg_mask, (9, 9), 0)
    _, fg_mask = cv2.threshold(fg_mask, 127, 255, cv2.THRESH_BINARY)

    # --- 2. Grayscale + global contrast stretch + gamma brighten ---
    # Plain CLAHE (local adaptive contrast) over-amplifies pore/stubble
    # micro-texture on a real (not flatly-lit-studio) phone photo — that
    # texture is exactly what makes ASCII portraits read as noisy static
    # instead of a face. Instead: stretch the *foreground* pixels' 3rd-
    # 97th percentile range to 0-1, then apply a gamma < 1 so only true
    # shadows (hair, glasses, brow/nose shading) stay dense — midtone
    # skin lifts toward white, which is what the ASCII ramp needs to
    # print an actual recognizable shape instead of a solid block.
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    fg_pixels = gray[fg_mask > 127]
    lo, hi = np.percentile(fg_pixels, 3), np.percentile(fg_pixels, 97)
    stretched = np.clip((gray - lo) / max(hi - lo, 1e-6), 0, 1)
    gamma = 0.55
    gray_boosted = (np.power(stretched, gamma) * 255).astype(np.uint8)

    # --- 3. Composite onto pure white using the fg mask ---
    white = np.full_like(gray_boosted, 255)
    alpha = fg_mask.astype(np.float32) / 255.0
    composited = (gray_boosted.astype(np.float32) * alpha + white.astype(np.float32) * (1 - alpha)).astype(np.uint8)

    cv2.imwrite(path_out, composited)
    print(f"wrote {path_out}  ({composited.shape[1]}x{composited.shape[0]})")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "source-photo.png"
    out = sys.argv[2] if len(sys.argv) > 2 else "source-prepped.png"
    prep(src, out)
