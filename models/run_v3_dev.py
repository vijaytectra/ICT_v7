import sys; sys.path.insert(0, r"C:\personal\ICT_v7")
import pandas as pd
from models.v3lab import IDX, port, st
pd.set_option("display.width", 210); f = lambda x: f"{x:.3f}"
ARMS = [("mss (LOCKED)", dict(trigger="mss")),
        ("cisd", dict(trigger="cisd")),
        ("cisd+mss", dict(trigger="cisd_mss")),
        ("reclaim", dict(trigger="reclaim")),
        ("mss  raid 09-12", dict(trigger="mss", raid_kz=(9, 12))),
        ("cisd raid 09-12", dict(trigger="cisd", raid_kz=(9, 12))),
        ("reclaim raid 09-12", dict(trigger="reclaim", raid_kz=(9, 12))),
        ("mss  raid 09-18", dict(trigger="mss", raid_kz=(9, 18))),
        ("cisd raid 09-18", dict(trigger="cisd", raid_kz=(9, 18))),
        ("reclaim raid 09-18", dict(trigger="reclaim", raid_kz=(9, 18))),
        ("mss  raid 15-18", dict(trigger="mss", raid_kz=(15, 18))),
        ("cisd raid 15-18", dict(trigger="cisd", raid_kz=(15, 18)))]
rows = [st(port(IDX, True, **d), nm, 108) for nm, d in ARMS]
print("=" * 126)
print("DEV MARKET — US indices 2015-2023 (9 years). Selection happens HERE and nowhere else.")
print("=" * 126)
r = pd.DataFrame(rows)
r.to_csv(r"C:\personal\ICT_v7\reports\v3_dev.csv", index=False)
print(r.to_string(index=False, float_format=f))
