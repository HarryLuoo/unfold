"""Figures for the quantum-geometry demo note. Run: python figures.py  (needs numpy and matplotlib;
writes figures/*.png next to this file)."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.size": 13, "mathtext.fontset": "cm", "font.family": "serif"})


def save(fig, name):
    for ext in ("png",):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"), dpi=200, bbox_inches="tight")
    plt.close(fig)


# Figure 1: winding numbers 0, 1, 2 about the origin
t = np.linspace(0, 2 * np.pi, 600)
curves = [(1.6 + 0.7 * np.cos(t), 0.9 + 0.7 * np.sin(t), 0),
          (1.1 * np.cos(t) + 0.25, 1.1 * np.sin(t), 1),
          (0.8 * np.cos(2 * t) + 0.5 * np.cos(-t), 0.8 * np.sin(2 * t) + 0.5 * np.sin(-t), 2)]
fig, axes = plt.subplots(1, 3, figsize=(10, 3.4))
for ax, (x, y, w) in zip(axes, curves):
    ax.plot(x, y, color="#1d4f91", lw=2)
    k = 150
    ax.annotate("", xy=(x[k + 4], y[k + 4]), xytext=(x[k], y[k]),
                arrowprops=dict(arrowstyle="-|>", color="#1d4f91", lw=2, mutation_scale=18))
    ax.plot(0, 0, "o", color="#c0392b", ms=7)
    ax.set_title(f"$w={w}$")
    ax.set_xlim(-1.6, 2.6); ax.set_ylim(-1.6, 1.9)
    ax.set_aspect("equal"); ax.axis("off")
save(fig, "winding")

# Figure 2: a loop of field directions on the Bloch sphere encloses solid angle Sigma
fig = plt.figure(figsize=(4.6, 4.6))
ax = fig.add_subplot(projection="3d")
u, v = np.linspace(0, 2 * np.pi, 60), np.linspace(0, np.pi, 30)
ax.plot_surface(np.outer(np.cos(u), np.sin(v)), np.outer(np.sin(u), np.sin(v)),
                np.outer(np.ones_like(u), np.cos(v)), color="#dfe6ee", alpha=0.35, linewidth=0)
th0 = 0.75
cu, cv = np.linspace(0, 2 * np.pi, 60), np.linspace(0, th0, 12)
ax.plot_surface(np.outer(np.cos(cu), np.sin(cv)), np.outer(np.sin(cu), np.sin(cv)),
                np.outer(np.ones_like(cu), np.cos(cv)), color="#f2a83b", alpha=0.6, linewidth=0)
ax.plot(np.sin(th0) * np.cos(cu), np.sin(th0) * np.sin(cu), np.cos(th0) * np.ones_like(cu), color="#c0392b", lw=2.5)
ax.quiver(0, 0, 0, np.sin(th0), 0, np.cos(th0), color="#1d4f91", lw=2, arrow_length_ratio=0.12)
ax.text2D(0.37, 0.58, r"$\hat{\mathbf{n}}$", transform=ax.transAxes, fontsize=18, color="#1d4f91")
ax.text(-0.15, -0.1, 1.12, r"$\Sigma$", fontsize=18, color="#7a4a00", zorder=10)
ax.set_box_aspect((1, 1, 1), zoom=1.55); ax.axis("off"); ax.view_init(elev=12, azim=20)
save(fig, "bloch")


# Figures 3 and 4: the Qi-Wu-Zhang model
def dvec(kx, ky, m):
    return np.stack([np.sin(kx), np.sin(ky), m + np.cos(kx) + np.cos(ky)])


def curvature(m, N=200):
    """Omega of the lower band, (1/2) n.(d_x n x d_y n), on an N x N grid of the zone."""
    k = np.linspace(0, 2 * np.pi, N, endpoint=False) + np.pi / N
    kx, ky = np.meshgrid(k, k, indexing="ij")
    h = 1e-5
    n = lambda a, b: (lambda d: d / np.linalg.norm(d, axis=0))(dvec(a, b, m))
    nx = (n(kx + h, ky) - n(kx - h, ky)) / (2 * h)
    ny = (n(kx, ky + h) - n(kx, ky - h)) / (2 * h)
    om = 0.5 * np.einsum("i...,i...", n(kx, ky), np.cross(nx, ny, axis=0))
    return k, om


ms = np.linspace(-3, 3, 241)
C = [curvature(m, 90)[1].sum() * (2 * np.pi / 90) ** 2 / (2 * np.pi) for m in ms]
kk = np.linspace(-np.pi, np.pi, 201)
KX, KY = np.meshgrid(kk, kk, indexing="ij")
gap = [2 * np.linalg.norm(dvec(KX, KY, m), axis=0).min() for m in ms]
fig, (a1, a2) = plt.subplots(2, 1, figsize=(6, 4.4), sharex=True)
a1.plot(ms, gap, color="#1d4f91", lw=2)
a1.set_ylabel("gap  $2\\min|\\mathbf{d}|$")
a2.plot(ms, np.round(C, 6), color="#c0392b", lw=2)
a2.set_ylabel("$C$"); a2.set_xlabel("$m$"); a2.set_yticks([-1, 0, 1])
for a in (a1, a2):
    for x0 in (-2, 0, 2):
        a.axvline(x0, color="0.6", lw=0.8, ls=":")
save(fig, "qwz_phase")
print("C at m = 1.0, -1.0, 3.0:", [round(C[np.argmin(abs(ms - x))], 3) for x in (1.0, -1.0, 3.0)])

k, om = curvature(1.6, 200)
fig, ax = plt.subplots(figsize=(4.8, 4))
lim = np.abs(om).max()
im = ax.pcolormesh(k, k, om.T, cmap="Blues_r", vmin=-lim, vmax=0, shading="auto")
ax.set_xlabel("$k_x$"); ax.set_ylabel("$k_y$"); ax.set_aspect("equal")
ax.set_xticks([0, np.pi, 2 * np.pi]); ax.set_xticklabels(["0", "$\\pi$", "$2\\pi$"])
ax.set_yticks([0, np.pi, 2 * np.pi]); ax.set_yticklabels(["0", "$\\pi$", "$2\\pi$"])
fig.colorbar(im, ax=ax, label="$\\Omega(\\mathbf{k})$")
save(fig, "qwz_curvature")
print("integral of Omega/2pi at m=1.6:", round(om.sum() * (2 * np.pi / 200) ** 2 / (2 * np.pi), 4))
