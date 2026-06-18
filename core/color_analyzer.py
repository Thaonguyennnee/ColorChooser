import cv2
import numpy as np

def calculate_color_stats(image_bgr, mask):
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    image_hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
    image_lab = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB)

    r, g, b = cv2.split(image_rgb)
    h, s, v = cv2.split(image_hsv)
    l, a_channel, b_channel = cv2.split(image_lab)

    channels = {
        'R': r, 'G': g, 'B': b,
        'H': h, 'S': s, 'V': v,
        'L': l, 'A': a_channel, 'B_Lab': b_channel
    }

    stats = {}
    for name, channel in channels.items():
        if len(mask.shape) == 3:
            mask = mask[:,:,0]
        masked_channel = channel[mask > 0]

        if len(masked_channel) > 0:
            mean_val = np.mean(masked_channel)
            std_val = np.std(masked_channel)
        else:
            mean_val = 0.0
            std_val = 0.0

        stats[f'{name}_mean'] = round(mean_val, 2)
        stats[f'{name}_std'] = round(std_val, 2)

    return stats
