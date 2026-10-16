"""Pre-registered analysis (docs/PREREGISTRATION_controversies.md).

Primary: S = z(null) + z(systematics) - z(confirm) - z(growth), z-scored over
the included historical cases; AUC of S for dissolved vs not dissolved
(confirmed + open), one-sided permutation p (H1: AUC > 0.5).
Then a one-feature logistic model on S scores the live controversies.
"""
import hashlib, json, math, random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGNS = {"null": 1, "systematics": 1, "confirm": -1, "growth": -1}
N_PERM, N_BOOT, SEED = 20000, 4000, 7


def auc(scores, labels):
    pos = [s for s, y in zip(scores, labels) if y]; neg = [s for s, y in zip(scores, labels) if not y]
    return sum((p > q) + 0.5 * (p == q) for p in pos for q in neg) / (len(pos) * len(neg))


def zfit(values):
    m = sum(values) / len(values); sd = math.sqrt(sum((v - m) ** 2 for v in values) / (len(values) - 1)) or 1.0
    return m, sd


def score(feats, norms):
    return sum(sign * (feats[k] - norms[k][0]) / norms[k][1] for k, sign in SIGNS.items())


def perm_p(scores, labels, observed, rng):
    hits = 0
    for _ in range(N_PERM):
        y = labels[:]; rng.shuffle(y); hits += auc(scores, y) >= observed - 1e-12
    return (hits + 1) / (N_PERM + 1)


def boot_ci(scores, labels, rng):
    pos = [i for i, y in enumerate(labels) if y]; neg = [i for i, y in enumerate(labels) if not y]; out = []
    for _ in range(N_BOOT):
        idx = [rng.choice(pos) for _ in pos] + [rng.choice(neg) for _ in neg]
        out.append(auc([scores[i] for i in idx], [labels[i] for i in idx]))
    out.sort(); return out[int(0.025 * N_BOOT)], out[int(0.975 * N_BOOT)]


def logistic(x, y, iters=20000, lr=0.05, l2=1e-3):
    a = b = 0.0
    for _ in range(iters):
        ga = gb = 0.0
        for xi, yi in zip(x, y):
            p = 1 / (1 + math.exp(-(a + b * xi))); ga += p - yi; gb += (p - yi) * xi
        a -= lr * ga / len(x); b -= lr * (gb / len(x) + l2 * b)
    return a, b


def evaluate(hist, rng, label):
    keys = sorted(hist)
    norms = {k: zfit([hist[c][k] for c in keys]) for k in SIGNS}
    s = [score(hist[c], norms) for c in keys]; y = [hist[c]["outcome"] == "dissolved" for c in keys]
    a = auc(s, y)
    res = dict(subset=label, n=len(keys), n_dissolved=sum(y), auc_S=a, perm_p_one_sided=perm_p(s, y, a, rng), ci95=boot_ci(s, y, rng))
    res["feature_auc"] = {k: auc([sign * hist[c][k] for c in keys], y) for k, sign in {**SIGNS, "exotic": 1, "log_n": -1}.items()}
    return res, norms, keys, s, y


def main():
    rng = random.Random(SEED)
    feats = json.loads((ROOT / "data/controversies/features.json").read_text())
    hist = {k: v for k, v in feats.items() if v["outcome"] != "prospective"}
    live = {k: v for k, v in feats.items() if v["outcome"] == "prospective"}
    primary, norms, keys, s, y = evaluate(hist, rng, "all included historical cases")
    firm, *_ = evaluate({k: v for k, v in hist.items() if not v["provisional"]}, rng, "excluding provisional labels")
    loo = []
    for i, k in enumerate(keys):  # leave-one-out: refit z-norms and logistic without case k
        rest = {c: hist[c] for c in keys if c != k}
        n_ = {f: zfit([rest[c][f] for c in rest]) for f in SIGNS}
        a_, b_ = logistic([score(rest[c], n_) for c in rest], [rest[c]["outcome"] == "dissolved" for c in rest])
        loo.append(1 / (1 + math.exp(-(a_ + b_ * score(hist[k], n_)))))
    a, b = logistic(s, y)
    forecast = {k: dict(S=score(v, norms), p_dissolved=1 / (1 + math.exp(-(a + b * score(v, norms)))), n=v["n"]) for k, v in sorted(live.items())}
    out = dict(primary=primary, sensitivity=firm,
               loo_auc=auc(loo, y), loo=dict(zip(keys, loo)),
               per_case={k: dict(S=si, outcome=hist[k]["outcome"], provisional=hist[k]["provisional"]) for k, si in zip(keys, s)},
               model=dict(intercept=a, slope=b, norms=norms), forecast=forecast)
    blob = json.dumps(out, indent=1, sort_keys=True)
    out_dir = ROOT / "results/controversies"; out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "analysis.json").write_text(blob)
    (out_dir / "FREEZE_forecast.json").write_text(json.dumps(dict(
        forecast=forecast, sha256_analysis=hashlib.sha256(blob.encode()).hexdigest(),
        sha256_features=hashlib.sha256((ROOT / "data/controversies/features.json").read_bytes()).hexdigest()), indent=1, sort_keys=True))
    print(json.dumps(dict(primary=primary, sensitivity=firm, loo_auc=out["loo_auc"], forecast=forecast), indent=1))


if __name__ == "__main__":
    main()
