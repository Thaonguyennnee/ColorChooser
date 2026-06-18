import cv2
import numpy as np

def detect_tube(image_bgr):
    h, w = image_bgr.shape[:2]

    blurred = cv2.GaussianBlur(image_bgr, (7, 7), 0)

    image_lab = cv2.cvtColor(blurred, cv2.COLOR_BGR2LAB)

    pixel_values = image_lab.reshape((-1, 3))
    pixel_values = np.float32(pixel_values)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 0.2)
    k = 2
    _, labels, centers = cv2.kmeans(pixel_values, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

    labels = labels.flatten()

    mask0 = (labels == 0).reshape((h, w)).astype(np.uint8) * 255
    mask1 = (labels == 1).reshape((h, w)).astype(np.uint8) * 255

    border_pixels_0 = np.sum(mask0[0, :] == 255) + np.sum(mask0[-1, :] == 255) + np.sum(mask0[:, 0] == 255) + np.sum(mask0[:, -1] == 255)
    border_pixels_1 = np.sum(mask1[0, :] == 255) + np.sum(mask1[-1, :] == 255) + np.sum(mask1[:, 0] == 255) + np.sum(mask1[:, -1] == 255)

    if border_pixels_0 < border_pixels_1:
        mask = mask0
    else:
        mask = mask1

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return None, None

    largest_contour = max(contours, key=cv2.contourArea)
    x, y, w_box, h_box = cv2.boundingRect(largest_contour)

    final_mask = np.zeros_like(mask)
    cv2.drawContours(final_mask, [largest_contour], -1, 255, -1)

    return final_mask, (x, y, w_box, h_box)
