import sys, cv2
im = cv2.imread(sys.argv[1]); x0, y0, x1, y1 = map(int, sys.argv[2:6]); out = sys.argv[6]
f = int(sys.argv[7]) if len(sys.argv) > 7 else 3; g = int(sys.argv[8]) if len(sys.argv) > 8 else 10
c = cv2.resize(im[y0:y1, x0:x1].copy(), None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
for x in range((x0 // g) * g, x1, g):
    if x < x0: continue
    X = (x - x0) * f; cv2.line(c, (X, 0), (X, c.shape[0]), (0, 0, 255) if x % (5 * g) == 0 else (128, 128, 128), 1)
    if x % (5 * g) == 0: cv2.putText(c, str(x), (X + 2, 12), 0, 0.4, (0, 0, 255), 1)
for y in range((y0 // g) * g, y1, g):
    if y < y0: continue
    Y = (y - y0) * f; cv2.line(c, (0, Y), (c.shape[1], Y), (0, 0, 255) if y % (5 * g) == 0 else (128, 128, 128), 1)
    if y % (5 * g) == 0: cv2.putText(c, str(y), (2, Y - 2), 0, 0.4, (0, 0, 255), 1)
cv2.imwrite(out, c)
