import sys, cv2, numpy as np, glob
fs = sorted(glob.glob(sys.argv[1] + '/p_*.png'))
def L(i): return cv2.imread(fs[i]).astype(np.float32)
d = [np.abs(L(i) - L(i + 1)).mean() for i in range(0, len(fs) - 1, max(1, len(fs) // 12))]
seam = np.abs(L(-1) - L(0)).mean()
print('typical consecutive diff %.2f (max %.2f), seam %.2f' % (np.mean(d), np.max(d), seam))
